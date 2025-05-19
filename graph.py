"""
LangGraph implementation for connecting the PydanticAI agents in a workflow.

This module creates a graph that connects all agents in the following order:
1. Fault_summary
2. Action_planner
3. Action_executor
4. Action_analyzer
"""

from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Optional, Annotated, Literal
from dataclasses import dataclass
from datetime import datetime
import os
import logging
import asyncio
import yaml
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langgraph.types import interrupt, Command
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

# Path to the network device inventory YAML file
inventory_path = "inventory/network_devices.yml"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_network_inventory(file_path: str) -> Dict[str, Any]:
    """
    Load network device inventory from a YAML file.
    
    This function will read in the details of a network device inventory
    from a YAML file into a Python dictionary. The inventory contains
    information about network devices such as hostname, IP address,
    device type, credentials, etc.
    
    Args:
        file_path: Path to the YAML file containing network inventory
        
    Returns:
        Dict[str, Any]: Dictionary containing network device inventory
        
    Future enhancements:
    - Add validation for required fields
    - Support for different inventory formats
    - Handle authentication information securely
    """
    # Stub function - will be implemented in the future
    return {}

# Load network inventory
network_inventory = load_network_inventory(inventory_path)

# Define the state for our graph
class NetworkTroubleshootingState(TypedDict):
    """State for the network troubleshooting workflow graph."""
    latest_user_message: str
    messages: Annotated[List[bytes], lambda x, y: x + y]
    inventory: Dict[str, Any]
    alert_raw_data: str
    fault_summary: Optional[FaultSummary]
    action_plan: Optional[List[TroubleshootingStep]]
    action_plan_history: Optional[List[TroubleshootingStep]]  # New field
    action_plan_remaining: Optional[List[TroubleshootingStep]]  # New field
    current_step_index: int
    execution_result: Optional[Dict[str, Any]]
    analysis_report: Optional[ActionAnalysisReport]
    device_driver: Optional[Any] # Placeholder for device driver
    device_facts: Dict[str, Any]  # Placeholder for device facts
    device_credentials: Optional[DeviceCredentials]
    settings: Dict[str, Any]  # Contains simulation_mode, test_mode, test_name, etc.
    test_data: Optional[Dict[str, Any]]  # Store loaded test data


# Function to load test data
def load_test_data(test_name: str) -> Dict[str, Any]:
    """Load test data from a YAML file."""
    try:
        test_file = Path(f"tests/test_{test_name}.yml")
        if not test_file.exists():
            logger.warning(f"Test file {test_file} not found")
            return {}
        
        with open(test_file, "r") as f:
            test_data = yaml.safe_load(f)
        
        logger.info(f"Loaded test data for {test_name}")
        return test_data
    except Exception as e:
        logger.error(f"Error loading test data: {e}")
        return {}

# Function to run the fault summary agent
async def run_fault_summary_node(state: NetworkTroubleshootingState, writer) -> NetworkTroubleshootingState:
    """Run the fault summary agent to analyze and summarize a network fault."""
    logger.info("Running fault summary agent")
    
    # Get the input text and settings from the state
    alert_raw_data = state["latest_user_message"]
    settings = state["settings"]
    test_data = {}
    
    # Handle test mode - load test data if test_mode is enabled
    if settings.get("test_mode", False):
        test_name = settings.get("test_name", "")
        if test_name:
            test_data = load_test_data(test_name)
            if test_data and "alert_payload" in test_data:
                # Use the test alert payload as input instead of user message
                alert_raw_data = test_data["alert_payload"]
                logger.info(f"Using test alert payload from test_{test_name}.yml")
    
    # Create dependencies for the fault summary agent
    fault_summary_deps = FaultSummaryDependencies(
        settings=settings,
        logger=logger
    )
    
    # Run the fault summary agent with dependencies
    result = await run_fault_summary(alert_raw_data, deps=fault_summary_deps)
    fault_summary = result.output

    # Generate human-readable output for the writer based on FaultSummary class structure with Markdown formatting
    writer(f"""## 📊 Fault Summary

**Title:** {fault_summary.title}  
**Summary:** {fault_summary.summary}  
**Device:** {fault_summary.hostname}  
**Severity:** {fault_summary.severity}  
**Timestamp:** {fault_summary.timestamp.strftime('%Y-%m-%d %H:%M:%S')}  
**Alert Details:** {fault_summary.metadata}
""")

    # Set device_credentials based upon the fault summary
    device_credentials = DeviceCredentials(
        hostname=fault_summary.hostname,
        device_type=os.getenv("DEVICE_TYPE", "cisco_ios"),
        username=os.getenv("DEVICE_USERNAME", "admin"),
        password=os.getenv("DEVICE_PASSWORD", "password"),
        port=int(os.getenv("DEVICE_PORT", "22")),
        secret=os.getenv("DEVICE_SECRET")
    )
    
    # Update the state with the fault summary and test data if available
    return {
        **state,
        "alert_raw_data": alert_raw_data,
        "fault_summary": fault_summary,
        "device_credentials": device_credentials,
        "test_data": test_data
    }

# Function to run the init_deps node for dependency initialization
async def run_init_deps_node(state: NetworkTroubleshootingState, writer) -> NetworkTroubleshootingState:
    """Initialize device dependencies before running the action planner."""
    logger.info("Running init_deps node")
    
    # Get settings and fault_summary from state
    settings = state["settings"]
    fault_summary = state["fault_summary"]
    inventory = network_inventory  # Load network inventory
    
    # Initialize device_facts with default values
    device_facts = {
        "reachable": True,
        "errors": []
    }
    
    # Initialize device_driver as None
    device_driver = None
    
    # Only perform actual device connection when not in simulation or test mode
    if not settings.get("simulation_mode", True) and not settings.get("test_mode", False):
        try:
            # Get hostname from fault summary
            hostname = fault_summary.hostname
            
            # Look up device details in inventory
            device_details = inventory.get(hostname, {})
            
            if not device_details:
                logger.warning(f"Device {hostname} not found in inventory")
                device_facts["reachable"] = False
                device_facts["errors"].append(f"Device {hostname} not found in inventory")
            else:
                # Generate NAPALM device driver
                # PLACEHOLDER: Code to initialize NAPALM driver based on device_details
                # device_driver = napalm.get_network_driver(device_details["driver"])
                # device = device_driver(hostname, username, password, optional_args=optional_args)
                # device.open()
                
                # Run get_facts on the driver
                # PLACEHOLDER: Code to retrieve facts from the device
                # device_facts = device.get_facts()
                # Additional facts can be collected here
                
                # For placeholder purposes
                device_driver = {"type": "napalm_driver", "device": hostname}
                device_facts = {
                    "hostname": hostname,
                    "vendor": "cisco",
                    "model": "CSR1000v",
                    "uptime": 12345,
                    "os_version": "16.9.3",
                    "serial_number": "9KLAVM0JJ62",
                    "reachable": True,
                    "errors": []
                }
                
                # Log successful connection
                logger.info(f"Successfully connected to {hostname}")
                
        except Exception as e:
            # Handle connection failures
            error_message = f"Failed to connect to device: {str(e)}"
            logger.error(error_message)
            
            # Update device_facts to indicate unreachable
            device_facts["reachable"] = False
            device_facts["errors"].append(error_message)
    
    # Generate output for the writer
    if device_facts["reachable"]:
        status = "✅ Device reachable"
    else:
        status = "❌ Device unreachable"
    
    writer(f"""## 🔌 Device Dependency Initialization

**Device:** {fault_summary.hostname}
**Status:** {status}

{"### Errors:" if device_facts["errors"] else ""}
{"".join([f"- {error}\n" for error in device_facts["errors"]])}
""")
    
    # Update the state with the initialized dependencies
    return {
        **state,
        "inventory": inventory,
        "device_driver": device_driver,
        "device_facts": device_facts
    }

# Function to run the action planner agent
async def run_action_planner_node(state: NetworkTroubleshootingState, writer) -> NetworkTroubleshootingState:
    """Run the action planner agent to create a troubleshooting plan."""
    logger.info("Running action planner agent")
    
    # Get the fault summary from the state
    fault_summary = state["fault_summary"]
    custom_instructions = state.get("custom_instructions", {})
    device_facts = state["device_facts"]
    settings = state["settings"]
    
    if not fault_summary:
        logger.warning("No fault summary found in state")
        return state
    
    # Create dependencies for the action planner
    deps = ActionPlannerDependencies(
        fault_summary=fault_summary,
        custom_instructions=custom_instructions,
        device_facts=device_facts,
        settings=settings,
        logger=logger
    )
    
    # Run the action planner agent with the dependencies
    result = await run_action_planner("", deps=deps)
    action_plan = result.output

    # Generate human-readable output for the writer with Markdown formatting
    steps_markdown = []
    for i, step in enumerate(action_plan):
        # Format commands as a bulleted list
        commands_list = "\n".join([f"  - `{cmd}`" for cmd in step.commands]) if step.commands else "  - None"
        
        steps_markdown.append(f"""### Step {i+1}: {step.description}
- **🔄 Action Type:** {step.action_type}
- **📟 Commands:** 
{commands_list}
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

async def run_action_router_node(state: NetworkTroubleshootingState, writer) -> NetworkTroubleshootingState | Command[Literal["action_executor", "result_summary"]]:
    """Router node that manages action plan workflow and handles approval requirements."""
    logger.info("Running action router node")
    
    # 1. Update action_plan_history by appending the latest executed step
    action_plan_history = state.get("action_plan_history", [])
    action_plan_remaining = state.get("action_plan_remaining", [])

    # TODO: Add something that checks to see if we're resuming after human interrupt (needs to use state data)

    # TODO: Update this one we start using action analyzer
    action_analysis = False

    if action_analysis and action_plan_remaining:
        executed_step = action_plan_remaining[0]
        # Add the executed step to history if we have one
        if executed_step:
            action_plan_history.append(executed_step)
        # Remove the first element since it's been executed
        action_plan_remaining = action_plan_remaining[1:]
    
    # 3. Check device reachability
    device_facts = state["device_facts"]
    if not device_facts.get("reachable", False):
        writer("⚠️ **Device is unreachable. Routing to result summary.**")
        # Use Command to route to the result_summary node
        return Command(
            update={
                "action_plan_history": action_plan_history,
                "action_plan_remaining": action_plan_remaining
            },
            goto="result_summary"
        )
    
    # Check if we have steps remaining
    if not action_plan_remaining:
        writer("⚠️ **No more steps to execute. Routing to result summary.**")
        # Use Command to route to the result_summary node
        return Command(
            update={
                "action_plan_history": action_plan_history,
                "action_plan_remaining": action_plan_remaining
            },
            goto="result_summary"
        )
    
    # 4. Get current_step
    current_step = action_plan_remaining[0]
    
    # 5. Write step details for review
    commands_text = "\n".join([f"- `{cmd}`" for cmd in current_step.commands]) if current_step.commands else "- No commands"
    # TODO: Update this to use the same format as the action analyzer
    writer(f"""## ⚡ Action Router - Step Review
    
**Step Description:** {current_step.description}

**Action Type:** {current_step.action_type}

**Commands to Execute:**
{commands_text}

**Expected Output:** {current_step.output_expectation}

**Requires Approval:** {"Yes" if current_step.requires_approval else "No"}
""")
    
    # 6. If action type is escalation, route to result summary
    if current_step.action_type == "escalation":
        writer("⚠️ **Escalation step detected. Routing to result summary.**")
        # Use Command to route to the result_summary node
        return Command(
            update={
                "action_plan_history": action_plan_history,
                "action_plan_remaining": action_plan_remaining
            },
            goto="result_summary"
        )

    # 6. Check if approval is required and prompt user if needed
    if current_step.requires_approval:
        writer("\n\n⚠️ **This step requires approval. Waiting for user confirmation...**")
        
        # Use interrupt with the detailed payload
        response_text = interrupt({})
        
        # Convert string response to boolean
        # Accept various forms of "yes" as approval
        if isinstance(response_text, str):
            response = response_text.lower().strip() in ["yes", "y", "true", "approve", "1"]
        else:
            # Handle case where response might already be a boolean
            response = bool(response_text)
        
        # 7-8. Handle user approval response
        if response:
            writer("✅ **Action approved by user. Proceeding to execution.**")
            return Command(
                update={
                    "action_plan_history": action_plan_history,
                    "action_plan_remaining": action_plan_remaining
                },
                goto="action_executor"
            )
        else:
            writer("🛑 **Action rejected by user. Routing to result summary.**")
            return Command(
                update={
                    "action_plan_history": action_plan_history,
                    "action_plan_remaining": action_plan_remaining
                },
                goto="result_summary"
            )
    
    # 9. No approval required, proceed to executor
    writer("✅ **No approval required. Proceeding to execution.**")
    return Command(
        update={
            "action_plan_history": action_plan_history,
            "action_plan_remaining": action_plan_remaining
        },
        goto="action_executor"
    )

# Function to run the action executor agent
async def run_action_executor_node(state: NetworkTroubleshootingState, writer) -> NetworkTroubleshootingState:
    """Run the action executor agent to execute the current step in the action plan."""
    logger.info("Running action executor agent")
    
    # Get the action plan and current step index from the state
    action_plan = state["action_plan"]
    current_step_index = state["current_step_index"]
    device_credentials = state["device_credentials"]
    settings = state["settings"]
    test_data = state.get("test_data", {})
    
    if not action_plan or current_step_index >= len(action_plan):
        logger.warning("No more steps to execute in the action plan")
        return state
    
    # Get the current step to execute
    current_step = action_plan[current_step_index]
    
    # Handle test mode - use command output from test data
    if settings.get("test_mode", False) and test_data:
        commands = current_step.commands
        # Get command output from test data or use default message
        #command_output = test_data.get("commands", {}).get(commands, "Output not available")
        
        # Create simulated result structure
        simulated_output = []
        for command in commands:
            command_output = test_data.get("commands", {}).get(command, "Output not available")
            simulated_output.append({"cmd": command, "output": command_output})

        command_outputs = simulated_output
        errors = []
        
    else: 
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

        command_outputs = result.output.command_outputs
        errors = result.output.errors

    
    
    # Format the commands, their outputs, and errors with Markdown
    commands_md = ""
    for cmd in command_outputs:
        commands_md += f"- `{cmd['cmd']}`\n"    

    command_outputs_md = ""
    for output in command_outputs:
        command_outputs_md += f"```\n{output['output']}\n```\n"
    
    errors_md = ""
    if errors:
        for error in errors:
            errors_md += f"- ❌ **Error:** {error}\n"
    else:
        errors_md = "✅ **No errors encountered**"

    # Generate human-readable output for the writer with Markdown formatting
    mode_text = ""
    if settings.get("simulation_mode", True):
        mode_text = "**⚠️ SIMULATION MODE ⚠️**"
    elif settings.get("test_mode", False):
        mode_text = "**✅ TEST MODE**"
    else:
        mode_text = "**🔄 ACTUAL EXECUTION**"
        
    writer(f"""## 🔧 Executing Action {current_step_index+1}/{len(action_plan)}

**Commands:** 
{commands_md}

{mode_text}

### Output:
{command_outputs_md}

### Status:
{errors_md}
""")
    
    # Update the state with the execution result
    return {
        **state,
        "execution_result": {
            "command_outputs": command_outputs,
            "errors": errors
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
    # Generate human-readable output for the writer with Markdown formatting
    commands_text = "\n".join([f"- `{cmd}`" for cmd in current_step.commands]) if current_step.commands else "- No commands"
    writer(f"""## 📋 Analysis of Step {current_step_index+1} Results

**Commands Analyzed:**
{commands_text}

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

async def run_result_summary_node(state: NetworkTroubleshootingState, writer) -> NetworkTroubleshootingState:
    """Generate a summary of troubleshooting results."""
    logger.info("Running result summary node")
    
    writer("""## 📋 Troubleshooting Results Summary
    
**This is a stub implementation of the result_summary node.**

This node will provide a comprehensive summary of all troubleshooting actions performed,
including successful and failed steps, and recommendations for next actions.
""")
    
    return state

# # Function to check if we should continue with the next step or end the workflow
# def should_continue_or_end(state: NetworkTroubleshootingState, writer) -> str:
#     """Decide whether to continue with the next step or end the workflow."""
#     action_plan = state["action_plan"]
#     current_step_index = state["current_step_index"]
    
#     if not action_plan or current_step_index >= len(action_plan):
#         logger.info("No more steps to execute, ending workflow")
#         writer("No more steps to execute, ending workflow")
#         return "end"
#     else:
#         logger.info(f"Moving to next step: {current_step_index + 1}/{len(action_plan)}")
#         return "continue"

# Build and compile the graph
def build_graph() -> StateGraph:
    """Build and compile the network troubleshooting workflow graph."""
    # Create a new state graph
    builder = StateGraph(NetworkTroubleshootingState)
    
    # Add nodes for each agent
    builder.add_node("fault_summary_node", run_fault_summary_node)
    builder.add_node("init_deps", run_init_deps_node)
    builder.add_node("action_planner", run_action_planner_node)
    builder.add_node("action_router", run_action_router_node)
    builder.add_node("action_executor", run_action_executor_node)
    builder.add_node("action_analyzer", run_action_analyzer_node)
    builder.add_node("result_summary", run_result_summary_node)
    
    # Add edges to connect the nodes
    builder.add_edge(START, "fault_summary_node")
    builder.add_edge("fault_summary_node", "init_deps")
    builder.add_edge("init_deps", "action_planner")
    builder.add_edge("action_planner", "action_router")
    
    # Let action_router use Command objects for dynamic routing
    builder.add_edge("action_executor", "action_analyzer")
    builder.add_edge("action_analyzer", "action_router")
    builder.add_edge("result_summary", END)
    
    # Add conditional logic for looping or ending the workflow
    # builder.add_conditional_edges(
    #     "action_analyzer",
    #     should_continue_or_end,
    #     {
    #         "continue": "action_executor",
    #         "end": END
    #     }
    # )
    
    return builder

builder = build_graph()

# Configure persistence with memory saver
memory = MemorySaver()

# Compile the graph
agentic_flow = builder.compile(checkpointer=memory)
