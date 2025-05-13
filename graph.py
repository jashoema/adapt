"""
LangGraph implementation for connecting the PydanticAI agents in a workflow.

This module creates a graph that connects all agents in the following order:
1. Fault_summary
2. Action_planner
3. Action_executor
4. Action_analyzer
"""

from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Optional
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
from agents.fault_summary import run as run_fault_summary, FaultSummary
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
    input: str
    fault_summary: Optional[FaultSummary]
    action_plan: Optional[List[TroubleshootingStep]]
    current_step_index: int
    execution_result: Optional[Dict[str, Any]]
    analysis_report: Optional[ActionAnalysisReport]
    device_credentials: Optional[DeviceCredentials]
    simulation_mode: bool

# Function to run the fault summary agent
async def run_fault_summary_node(state: NetworkTroubleshootingState) -> NetworkTroubleshootingState:
    """Run the fault summary agent to analyze and summarize a network fault."""
    logger.info("Running fault summary agent")
    
    # Get the input text from the state
    input_text = state["input"]
    
    # Run the fault summary agent
    result = await run_fault_summary(input_text)
    fault_summary = result.output
    
    # Update the state with the fault summary
    return {
        **state,
        "fault_summary": fault_summary
    }

# Function to run the action planner agent
async def run_action_planner_node(state: NetworkTroubleshootingState) -> NetworkTroubleshootingState:
    """Run the action planner agent to create a troubleshooting plan."""
    logger.info("Running action planner agent")
    
    # Get the fault summary from the state
    fault_summary = state["fault_summary"]
    
    if not fault_summary:
        logger.warning("No fault summary found in state")
        return state
    
    # Create dependencies for the action planner
    deps = ActionPlannerDependencies(fault_summary=fault_summary)
    
    # Run the action planner agent with the fault summary
    result = await run_action_planner("", deps=deps)
    action_plan = result.output
    
    # Update the state with the action plan and set current step to 0
    return {
        **state,
        "action_plan": action_plan,
        "current_step_index": 0
    }

# Function to run the action executor agent
async def run_action_executor_node(state: NetworkTroubleshootingState) -> NetworkTroubleshootingState:
    """Run the action executor agent to execute the current step in the action plan."""
    logger.info("Running action executor agent")
    
    # Get the action plan and current step index from the state
    action_plan = state["action_plan"]
    current_step_index = state["current_step_index"]
    device_credentials = state["device_credentials"]
    simulation_mode = state["simulation_mode"]
    
    if not action_plan or current_step_index >= len(action_plan):
        logger.warning("No more steps to execute in the action plan")
        return state
    
    # Get the current step to execute
    current_step = action_plan[current_step_index]
    
    # Create dependencies for the action executor
    deps = ActionExecutorDeps(
        current_action=current_step,
        simulation_mode=simulation_mode,
        device=device_credentials,
        client=AsyncClient()
    )
    
    # Run the action executor agent for the current step
    result = await run_action_executor(deps=deps)
    
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
async def run_action_analyzer_node(state: NetworkTroubleshootingState) -> NetworkTroubleshootingState:
    """Run the action analyzer agent to analyze the output of the executed step."""
    logger.info("Running action analyzer agent")
    
    # Get the necessary state data
    action_plan = state["action_plan"]
    current_step_index = state["current_step_index"]
    execution_result = state["execution_result"]
    fault_summary = state["fault_summary"]
    
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
        current_step=current_step
    )
    
    # Run the action analyzer agent
    result = await run_action_analyzer(deps=deps)
    analysis_report = result.output
    
    # Increment the current step index to move to the next step
    next_step_index = current_step_index + 1
    
    # Update the state with the analysis report and next step index
    return {
        **state,
        "analysis_report": analysis_report,
        "current_step_index": next_step_index
    }

# Function to check if we should continue with the next step or end the workflow
def should_continue_or_end(state: NetworkTroubleshootingState) -> str:
    """Decide whether to continue with the next step or end the workflow."""
    action_plan = state["action_plan"]
    current_step_index = state["current_step_index"]
    
    if not action_plan or current_step_index >= len(action_plan):
        logger.info("No more steps to execute, ending workflow")
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
    
    # Configure persistence with memory saver
    memory = MemorySaver()
    
    # Compile the graph
    return builder.compile(checkpointer=memory)

# Initialize the state for the workflow
def initialize_state(
    input_text: str,
    device_credentials: DeviceCredentials,
    simulation_mode: bool = True
) -> NetworkTroubleshootingState:
    """Initialize the state for the network troubleshooting workflow."""
    return {
        "input": input_text,
        "fault_summary": None,
        "action_plan": None,
        "current_step_index": 0,
        "execution_result": None,
        "analysis_report": None,
        "device_credentials": device_credentials,
        "simulation_mode": simulation_mode
    }

# Function to run the graph
async def run_graph(
    input_text: str,
    device_hostname: str = "192.0.2.100",
    device_type: str = "cisco_ios",
    simulation_mode: bool = True
) -> Dict[str, Any]:
    """
    Run the network troubleshooting workflow graph with the given input.
    
    Args:
        input_text: The network fault description or alert
        device_hostname: The hostname or IP of the target device
        device_type: The type of device (e.g., cisco_ios, juniper)
        simulation_mode: Whether to simulate command execution or use real devices
        
    Returns:
        The final state of the workflow
    """
    # Create device credentials
    device_credentials = DeviceCredentials(
        hostname=device_hostname,
        device_type=device_type,
        username=os.getenv("DEVICE_USERNAME", "admin"),
        password=os.getenv("DEVICE_PASSWORD", "password"),
        port=int(os.getenv("DEVICE_PORT", "22")),
        secret=os.getenv("DEVICE_SECRET")
    )
    
    # Initialize the state
    initial_state = initialize_state(
        input_text=input_text,
        device_credentials=device_credentials,
        simulation_mode=simulation_mode
    )
    
    # Build the graph
    graph = build_graph()
    
    # Generate a unique thread ID for this troubleshooting session
    import uuid
    thread_id = str(uuid.uuid4())
    
    # Configure stream mode
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    # Run the graph
    final_state = await graph.ainvoke(initial_state, config)
    
    return final_state
