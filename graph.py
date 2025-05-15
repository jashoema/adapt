"""
LangGraph implementation for connecting the PydanticAI agents in a workflow.

This module creates a graph that connects all agents in the following order:
1. Fault_summary
2. Action_planner
3. Action_executor
4. Action_analyzer
"""

from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from dataclasses import dataclass
from datetime import datetime
import os
import logging
import asyncio

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from httpx import AsyncClient

# Import agents
from agents.fault_summary import run as run_fault_summary, FaultSummary, FaultSummaryDependencies
from agents.action_planner import run as run_action_planner, TroubleshootingStep, ActionPlannerDependencies
from agents.action_executor import run as run_action_executor, DeviceCredentials, ActionExecutorDeps
from agents.action_analyzer import run as run_action_analyzer, ActionAnalysisReport, ActionAnalyzerDependencies

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the state for our graph
class NetworkTroubleshootingState(TypedDict):
    """State for the network troubleshooting workflow graph."""
    latest_user_message: str
    messages: Annotated[List[bytes], lambda x, y: x + y]
    fault_summary: Optional[FaultSummary]
    action_plan: Optional[List[TroubleshootingStep]]
    current_step_index: int
    execution_result: Optional[Dict[str, Any]]
    analysis_report: Optional[ActionAnalysisReport]
    device_credentials: Optional[DeviceCredentials]
    settings: Dict[str, bool]

# Function to run the fault summary agent
async def run_fault_summary_node(state: NetworkTroubleshootingState, writer) -> NetworkTroubleshootingState:
    """Run the fault summary agent to analyze and summarize a network fault."""
    logger.info("Running fault summary agent")
    
    # Get the input text from the state
    input_text = state["latest_user_message"]
    settings = state["settings"]
    
    # Create dependencies for the fault summary agent
    fault_summary_deps = FaultSummaryDependencies(
        settings=settings,
        logger=logger
    )
    
    # Run the fault summary agent with dependencies
    result = await run_fault_summary(input_text, deps=fault_summary_deps)
    fault_summary = result.output

    # Generate human-readable output for the writer based on FaultSummary class structure with Markdown formatting
    writer(f"""## 📊 Fault Summary

**Title:** {fault_summary.title}  
**Summary:** {fault_summary.summary}  
**Device:** {fault_summary.hostname} ({fault_summary.operating_system})  
**Severity:** {fault_summary.severity}  
**Timestamp:** {fault_summary.timestamp.strftime('%Y-%m-%d %H:%M:%S')}  
**Alert Details:** {fault_summary.original_alert_details}
""")

    # Set device_credentials based upon the fault summary
    device_credentials = DeviceCredentials(
        hostname=fault_summary.hostname,
        device_type=fault_summary.operating_system,
        username=os.getenv("DEVICE_USERNAME", "admin"),
        password=os.getenv("DEVICE_PASSWORD", "password"),
        port=int(os.getenv("DEVICE_PORT", "22")),
        secret=os.getenv("DEVICE_SECRET")
    )
    
    # Update the state with the fault summary
    return {
        **state,
        "fault_summary": fault_summary,
        "device_credentials": device_credentials
    }

# Function to run the action planner agent
async def run_action_planner_node(state: NetworkTroubleshootingState, writer) -> NetworkTroubleshootingState:
    """Run the action planner agent to create a troubleshooting plan."""
    logger.info("Running action planner agent")
    
    # Get the fault summary from the state
    fault_summary = state["fault_summary"]
    settings = state["settings"]
    
    if not fault_summary:
        logger.warning("No fault summary found in state")
        return state
    
    # Create dependencies for the action planner
    deps = ActionPlannerDependencies(
        fault_summary=fault_summary,
        settings=settings,
        logger=logger
    )
    
    # Run the action planner agent with the dependencies
    result = await run_action_planner("", deps=deps)
    action_plan = result.output

    # Generate human-readable output for the writer with Markdown formatting
    steps_markdown = []
    for i, step in enumerate(action_plan):
        steps_markdown.append(f"""### Step {i+1}: {step.description}
- **📟 Command:** `{step.command}`
- **🔍 Expected Output:** {step.output_expectation}
- **⚠️ Requires Approval:** {'Yes' if step.requires_approval else 'No'}
""")
    
    writer(f"""## 🔍 Action Plan

**Total Steps:** {len(action_plan)}

{''.join(steps_markdown)}
""")
    
    # Update the state with the action plan and set current step to 0
    return {
        **state,
        "action_plan": action_plan,
        "current_step_index": 0
    }

# Function to run the action executor agent
async def run_action_executor_node(state: NetworkTroubleshootingState, writer) -> NetworkTroubleshootingState:
    """Run the action executor agent to execute the current step in the action plan."""
    logger.info("Running action executor agent")
    
    # Get the action plan and current step index from the state
    action_plan = state["action_plan"]
    current_step_index = state["current_step_index"]
    device_credentials = state["device_credentials"]
    settings = state["settings"]
    
    if not action_plan or current_step_index >= len(action_plan):
        logger.warning("No more steps to execute in the action plan")
        return state
    
    # Get the current step to execute
    current_step = action_plan[current_step_index]
    
    # Create dependencies for the action executor
    deps = ActionExecutorDeps(
        current_action=current_step,
        settings=settings,
        device=device_credentials,
        client=AsyncClient(),
        logger=logger
    )
    
    # Run the action executor agent for the current step
    result = await run_action_executor(deps=deps)

    # Format the command outputs and errors with Markdown
    command_outputs_md = ""
    for output in result.output.command_outputs:
        command_outputs_md += f"```\n{output['output']}\n```\n"
    
    errors_md = ""
    if result.output.errors:
        for error in result.output.errors:
            errors_md += f"- ❌ **Error:** {error}\n"
    else:
        errors_md = "✅ **No errors encountered**"

    # Generate human-readable output for the writer with Markdown formatting
    writer(f"""## 🔧 Executing Action {current_step_index+1}/{len(action_plan)}

**Command:** `{current_step.command}`

{f'**⚠️ SIMULATION MODE ⚠️**' if settings.get("simulation_mode", True) else '**🔄 ACTUAL EXECUTION**'}

### Output:
{command_outputs_md}

### Status:
{errors_md}
""")
    
    # Update the state with the execution result
    return {
        **state,
        "execution_result": {
            "command_outputs": result.output.command_outputs,
            "simulation_mode": result.output.simulation_mode,
            "errors": result.output.errors
        }
    }

# Function to run the action analyzer agent
async def run_action_analyzer_node(state: NetworkTroubleshootingState, writer) -> NetworkTroubleshootingState:
    """Run the action analyzer agent to analyze the output of the executed step."""
    logger.info("Running action analyzer agent")
    
    # Get the necessary state data
    action_plan = state["action_plan"]
    current_step_index = state["current_step_index"]
    execution_result = state["execution_result"]
    fault_summary = state["fault_summary"]
    settings = state["settings"]
    
    if not action_plan or not execution_result:
        logger.warning("Missing action plan or execution result in state")
        return state
    
    # Get the current step
    current_step = action_plan[current_step_index]
    
    # Create the executor output object for the analyzer
    executor_output = type('ActionExecutorOutput', (), {
        'command_outputs': execution_result["command_outputs"],
        'simulation_mode': execution_result["simulation_mode"],
        'errors': execution_result["errors"]
    })
    
    # Create dependencies for the action analyzer
    deps = ActionAnalyzerDependencies(
        executor_output=executor_output,
        action_plan=action_plan,
        fault_summary=fault_summary,
        current_step=current_step,
        settings=settings,
        logger=logger
    )
    
    # Run the action analyzer agent
    result = await run_action_analyzer(deps=deps)
    analysis_report = result.output
    
    # Format findings, issues and recommendations with Markdown
    key_findings_md = ""
    if analysis_report.key_findings:
        for finding in analysis_report.key_findings:
            key_findings_md += f"- {finding}\n"
    else:
        key_findings_md = "- No findings reported\n"
        
    issues_md = ""
    if analysis_report.issues_identified:
        for issue in analysis_report.issues_identified:
            issues_md += f"- {issue}\n"
    else:
        issues_md = "- No issues identified\n"
        
    recommendations_md = ""
    if analysis_report.recommendations:
        for rec in analysis_report.recommendations:
            recommendations_md += f"- {rec}\n"
    else:
        recommendations_md = "- No specific recommendations\n"
    
    # Generate human-readable output for the writer with Markdown formatting
    writer(f"""## 📋 Analysis of Step {current_step_index+1} Results

**Command Analyzed:** `{current_step.command}`

### 📝 Key Findings:
{key_findings_md}

### ⚠️ Issues Identified:
{issues_md}

### 🔮 Recommendations:
{recommendations_md}

**🎯 Confidence Level:** {analysis_report.confidence_level}
""")

    # Increment the current step index to move to the next step
    next_step_index = current_step_index + 1
    
    # Update the state with the analysis report and next step index
    return {
        **state,
        "analysis_report": analysis_report,
        "current_step_index": next_step_index
    }

# Function to check if we should continue with the next step or end the workflow
def should_continue_or_end(state: NetworkTroubleshootingState, writer) -> str:
    """Decide whether to continue with the next step or end the workflow."""
    action_plan = state["action_plan"]
    current_step_index = state["current_step_index"]
    
    if not action_plan or current_step_index >= len(action_plan):
        logger.info("No more steps to execute, ending workflow")
        writer("No more steps to execute, ending workflow")
        return "end"
    else:
        logger.info(f"Moving to next step: {current_step_index + 1}/{len(action_plan)}")
        return "continue"

# Build and compile the graph
def build_graph() -> StateGraph:
    """Build and compile the network troubleshooting workflow graph."""
    # Create a new state graph
    builder = StateGraph(NetworkTroubleshootingState)
    
    # Add nodes for each agent
    builder.add_node("fault_summary_node", run_fault_summary_node)
    builder.add_node("action_planner", run_action_planner_node)
    builder.add_node("action_executor", run_action_executor_node)
    builder.add_node("action_analyzer", run_action_analyzer_node)
    
    # Add edges to connect the nodes
    builder.add_edge(START, "fault_summary_node")
    builder.add_edge("fault_summary_node", "action_planner")
    builder.add_edge("action_planner", "action_executor")
    builder.add_edge("action_executor", "action_analyzer")
    
    # Add conditional logic for looping or ending the workflow
    builder.add_conditional_edges(
        "action_analyzer",
        should_continue_or_end,
        {
            "continue": "action_executor",
            "end": END
        }
    )
    
    return builder

builder = build_graph()

# Configure persistence with memory saver
memory = MemorySaver()

# Compile the graph
agentic_flow = builder.compile(checkpointer=memory)
