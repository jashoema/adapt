from __future__ import annotations
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import os
import asyncio
import logging
import time

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer

from app.models.network_alert import NetworkAlert
from app.models.action_plan import ActionPlan, ActionStep
from app.models.command_output import CommandOutput
from app.models.troubleshooting_state import TroubleshootingState, AnalysisResult
import logfire

logfire.configure(send_to_logfire='if-token-present')

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure LLM and Agents
model_name = os.getenv('PRIMARY_MODEL', 'gpt-4o-mini')
base_url = os.getenv('BASE_URL', 'https://api.openai.com/v1')
api_key = os.getenv('LLM_API_KEY', 'no-llm-api-key-provided')
use_simulation = os.getenv('USE_SIMULATION', 'True').lower() == 'true'
simulation_delay = float(os.getenv('SIMULATION_DELAY', '1.0'))

# Define NetworkDeviceParams model for command execution
class NetworkDeviceParams(BaseModel):
    """Parameters for connecting to a network device."""
    hostname: str = Field(..., description="Device hostname or IP address")
    username: Optional[str] = Field(None, description="SSH username for device access")
    password: Optional[str] = Field(None, description="SSH password for device access")
    device_type: str = Field("cisco_ios", description="Device type for Netmiko")
    timeout: int = Field(30, description="Command execution timeout in seconds")

# Define CommandExecutorDeps model for command executor agent
class CommandExecutorDeps(BaseModel):
    """Dependencies for the command executor agent."""
    use_simulation: bool = Field(False, description="Whether to use simulated device responses")
    simulation_delay: float = Field(1.0, description="Simulated delay in seconds for command execution")

# Define command executor agent with system prompt that includes instructions on tool selection
command_executor_agent = Agent(
    OpenAIModel(model_name, base_url=base_url, api_key=api_key),
    system_prompt="""
    You are a network automation assistant specialized in executing commands on network devices.
    Your primary responsibility is to execute CLI commands on network devices and return the output.
    
    You have two tools at your disposal:
    1. execute_cli_command: For executing show/operational commands
    2. execute_cli_config: For executing configuration commands
    
    You must select the appropriate tool based on the command type:
    - Use execute_cli_command for information gathering commands like 'show', 'ping', 'traceroute', etc.
    - Use execute_cli_config for configuration commands that modify the device, like 'configure terminal', etc.
    
    When in simulation mode, you will simulate realistic responses for network commands:
    - Generate output that exactly matches the command syntax and formatting of the specified device type
    - Include proper headers, spacing, and alignment as would appear on a real device
    - For error conditions, include accurate error messages in the proper format
    - Base your responses on typical network device behavior and common network configurations
    - Include realistic values for interfaces, routes, neighbors, etc.
    
    For real command execution via Netmiko:
    - Handle SSH connections to the device securely
    - Execute commands and capture output accurately
    - Handle timeouts and connection errors appropriately
    
    Always maintain security best practices:
    - Never expose sensitive information in logs or outputs
    - Handle authentication information securely
    - Report errors accurately without exposing internal system details
    """,
    deps_type=CommandExecutorDeps,
)

# Define command executor tools
@command_executor_agent.tool
async def execute_cli_command(
    ctx: RunContext[CommandExecutorDeps],
    device_params: NetworkDeviceParams,
    command: str
) -> str:
    """
    Execute a CLI command on a network device and return the output.
    
    This tool executes non-configuration (show/operational) commands on a network
    device using Netmiko. In simulation mode, it generates realistic device responses
    using the LLM.
    
    Args:
        ctx: The agent context with dependencies
        device_params: Connection parameters for the network device
        command: The command to execute on the device
        
    Returns:
        The output from the device for the executed command
    """
    # Simulate execution if in simulation mode
    if ctx.deps.use_simulation:
        # Add simulated delay to mimic network latency
        await asyncio.sleep(ctx.deps.simulation_delay)
        
        # Use the LLM to generate a realistic response based on the command
        simulation_prompt = f"""
        Simulate the output of the following network command:
        
        Device Information:
        - Hostname: {device_params.hostname}
        - Device Type: {device_params.device_type}
        
        Command to execute:
        {command}
        
        Generate the exact output as it would appear on this device type.
        Include proper formatting, headers, and typical values.
        If the command would fail, include appropriate error messages.
        """
        
        # Call the LLM to generate the simulated output
        # We're using the same agent here for simplicity
        simulated_output = await ctx.agent.run(simulation_prompt)
        return simulated_output.data
    else:
        # Execute real command via Netmiko
        logger.info(f"Executing command '{command}' on {device_params.hostname} via Netmiko")
        
        try:
            # Placeholder for actual Netmiko implementation
            # from netmiko import ConnectHandler
            # 
            # device = {
            #     'device_type': device_params.device_type,
            #     'host': device_params.hostname,
            #     'username': device_params.username,
            #     'password': device_params.password,
            #     'timeout': device_params.timeout,
            # }
            # 
            # with ConnectHandler(**device) as conn:
            #     output = conn.send_command(command)
            #     return output
            
            # For now, return simulated output since Netmiko is not implemented
            await asyncio.sleep(0.5)  # Simulate connection time
            return f"Real execution of '{command}' on {device_params.hostname} (Netmiko implementation pending)"
            
        except Exception as e:
            logger.error(f"Error executing command via Netmiko: {str(e)}")
            raise

@command_executor_agent.tool
async def execute_cli_config(
    ctx: RunContext[CommandExecutorDeps],
    device_params: NetworkDeviceParams,
    config_commands: Union[str, List[str]]
) -> str:
    """
    Execute configuration commands on a network device.
    
    This tool executes configuration commands on a network device using Netmiko.
    It handles entering configuration mode, executing the commands, and exiting 
    configuration mode. In simulation mode, it generates realistic responses using the LLM.
    
    Args:
        ctx: The agent context with dependencies
        device_params: Connection parameters for the network device
        config_commands: One or more configuration commands to execute
        
    Returns:
        The output from the device for the executed configuration commands
    """
    # Convert single command to list if needed
    if isinstance(config_commands, str):
        config_commands = [config_commands]
        
    # Simulate execution if in simulation mode
    if ctx.deps.use_simulation:
        # Add simulated delay to mimic network latency
        await asyncio.sleep(ctx.deps.simulation_delay)
        
        # Format the commands for the simulation prompt
        commands_str = "\n".join(config_commands)
        
        # Use the LLM to generate a realistic response based on the config commands
        simulation_prompt = f"""
        Simulate the output of the following network configuration commands:
        
        Device Information:
        - Hostname: {device_params.hostname}
        - Device Type: {device_params.device_type}
        
        Configuration commands to execute:
        {commands_str}
        
        Generate the exact output as it would appear on this device type.
        Include any responses or errors that would be displayed during configuration.
        For successful configuration commands, often there is no output.
        If the commands would fail, include appropriate error messages in the device's format.
        """
        
        # Call the LLM to generate the simulated output
        simulated_output = await ctx.agent.run(simulation_prompt)
        return simulated_output.data
    else:
        # Execute real configuration via Netmiko
        logger.info(f"Executing config commands on {device_params.hostname} via Netmiko")
        
        try:
            # Placeholder for actual Netmiko implementation
            # from netmiko import ConnectHandler
            # 
            # device = {
            #     'device_type': device_params.device_type,
            #     'host': device_params.hostname,
            #     'username': device_params.username,
            #     'password': device_params.password,
            #     'timeout': device_params.timeout,
            # }
            # 
            # with ConnectHandler(**device) as conn:
            #     output = conn.send_config_set(config_commands)
            #     return output
            
            # For now, return simulated output since Netmiko is not implemented
            await asyncio.sleep(0.5)  # Simulate connection time
            return f"Real configuration of '{' '.join(config_commands)}' on {device_params.hostname} (Netmiko implementation pending)"
            
        except Exception as e:
            logger.error(f"Error executing config commands via Netmiko: {str(e)}")
            raise

# Define agent for fault summary generation
fault_summary_agent = Agent(
    OpenAIModel(model_name, base_url=base_url, api_key=api_key),
    system_prompt="""
    You are a network troubleshooting expert who specializes in analyzing network alert data.
    Your job is to generate a concise yet comprehensive summary of a network fault based on alert information.
    
    The summary should:
    1. Clearly identify the affected device and any services impacted
    2. Analyze the alert message for potential root causes
    3. Provide context about the severity and potential business impact
    4. Highlight any key information from the metadata that might be relevant
    
    Keep your summary factual and avoid speculation beyond what can be reasonably inferred from the data.
    """
)

# Define agent for action plan generation
action_plan_agent = Agent(
    OpenAIModel(model_name, base_url=base_url, api_key=api_key),
    system_prompt="""
    You are a network troubleshooting expert who specializes in creating detailed troubleshooting plans.
    Given a summary of a network fault, create a step-by-step troubleshooting plan with specific commands to execute.
    
    For each step, provide:
    1. A clear description of what this diagnostic step will check
    2. The exact command to execute on the device (use standard Cisco IOS, Juniper, or vendor-specific syntax as appropriate)
    3. What you expect to find in the output and how it relates to diagnosing the issue
    4. Whether this step requires approval (mark as requiring approval if it modifies configuration or impacts service)
    
    Start with non-intrusive information gathering commands before recommending any configuration changes.
    Your plan should systematically isolate the fault domain and identify the root cause.
    """
)

# Define agent for command output analysis
output_analysis_agent = Agent(
    OpenAIModel(model_name, base_url=base_url, api_key=api_key),
    system_prompt="""
    You are a network troubleshooting expert who analyzes command outputs from network devices.
    Your task is to analyze the output of a network command and extract meaningful insights.
    
    Your analysis should:
    1. Identify any abnormal values, errors, or warning messages in the output
    2. Determine if the output confirms or refutes the suspected issue
    3. Extract key metrics or status indicators relevant to the troubleshooting
    4. Recommend next steps based on this output
    
    Be precise and technical in your analysis. Reference specific lines in the output that support your conclusions.
    If you identify a clear root cause, highlight it prominently in your analysis.
    """
)

# Define agent for final report generation
final_report_agent = Agent(
    OpenAIModel(model_name, base_url=base_url, api_key=api_key),
    system_prompt="""
    You are a network troubleshooting expert who creates final summary reports of troubleshooting activities.
    Given the complete troubleshooting state, create a clear, comprehensive report of the troubleshooting process.
    
    Your report should include:
    1. A summary of the original alert and the identified fault
    2. A chronological summary of the troubleshooting steps taken and their outcomes
    3. The root cause(s) identified during troubleshooting
    4. Actions taken to resolve the issue or recommendations for resolution
    5. Recommendations for preventing similar issues in the future
    
    Be factual and technical but also ensure your report is understandable to technical management.
    Include specific commands and outputs only when they are directly relevant to understanding the issue.
    """
)

# Define the state for our graph
class TroubleshootingGraphState(TypedDict):
    state: TroubleshootingState
    human_feedback: Optional[str]
    requires_human_approval: bool
    
# Function to generate fault summary
async def generate_fault_summary(state: TroubleshootingGraphState):
    current_state = state["state"]
    alert = current_state.alert
    
    # Create prompt with alert details
    prompt = f"""
    Please analyze this network alert and provide a comprehensive fault summary:
    
    Device: {alert.hostname} (Type: {alert.device_type})
    Alert Message: {alert.alert_message}
    Severity: {alert.severity}
    Timestamp: {alert.timestamp}
    Source: {alert.source_system or "Unknown"}
    Affected Services: {', '.join(alert.affected_services) if alert.affected_services else "None specified"}
    
    Additional Context:
    {alert.metadata}
    
    Based on this alert, provide a concise but comprehensive summary of the fault.
    """
    
    logger.info(f"Generating fault summary for alert on {alert.hostname}")
    
    # Run the fault summary agent
    result = await fault_summary_agent.run(prompt)
    fault_summary = result.data
    
    # Update the state with the fault summary
    current_state.fault_summary = fault_summary
    
    return {"state": current_state}

# Function to generate action plan
async def generate_action_plan(state: TroubleshootingGraphState):
    current_state = state["state"]
    alert = current_state.alert
    fault_summary = current_state.fault_summary
    
    # Create prompt for action plan generation
    prompt = f"""
    Based on the following fault summary, create a detailed troubleshooting action plan:
    
    Device Information:
    - Hostname: {alert.hostname}
    - Device Type: {alert.device_type}
    
    Fault Summary:
    {fault_summary}
    
    Create a step-by-step troubleshooting plan for diagnosing and resolving this issue.
    For each step, include:
    1. Step description
    2. Exact command to execute (if applicable)
    3. Expected output and what to look for
    4. Whether the step requires approval or is service-impacting
    
    Return your response in a structured format that I can parse into individual steps.
    """
    
    logger.info(f"Generating action plan for {alert.hostname}")
    
    # Run the action plan agent
    result = await action_plan_agent.run(prompt)
    plan_text = result.data
    
    # Process the action plan text into structured steps
    action_steps = await parse_action_plan(plan_text)
    
    # Create the ActionPlan object
    action_plan = ActionPlan(
        steps=action_steps,
        current_step_index=0,
        fault_summary=fault_summary,
        estimated_completion_time=sum(step.estimated_duration or 0 for step in action_steps),
        requires_manual_intervention=any(step.requires_approval for step in action_steps)
    )
    
    # Update the state with the action plan
    current_state.action_plan = action_plan
    
    # Check if the first step requires human approval
    requires_human_approval = action_steps[0].requires_approval if action_steps else False
    
    return {
        "state": current_state,
        "requires_human_approval": requires_human_approval
    }

# Function to execute the next step in the action plan
async def execute_action_step(state: TroubleshootingGraphState):
    current_state = state["state"]
    action_plan = current_state.action_plan
    current_step_index = action_plan.current_step_index
    
    # Get the current step
    if current_step_index >= len(action_plan.steps):
        # No more steps, move to final report
        logger.info("No more steps to execute, moving to final report")
        current_state.status = "completed"
        return {"state": current_state}
    
    current_step = action_plan.steps[current_step_index]
    
    # Check if this step requires human approval
    if current_step.requires_approval and not state.get("human_feedback"):
        logger.info(f"Step {current_step.step_number} requires human approval")
        return {"state": current_state, "requires_human_approval": True}
    
    # Execute the command on the device
    if current_step.command:
        logger.info(f"Executing command: {current_step.command} on {current_state.alert.hostname}")
        
        start_time = time.time()
        
        # Prepare device parameters
        device_params = NetworkDeviceParams(
            hostname=current_state.alert.hostname,
            device_type=current_state.alert.device_type
        )
        
        # Set up dependencies
        deps = CommandExecutorDeps(
            use_simulation=use_simulation,
            simulation_delay=simulation_delay
        )
        
        # Let the agent determine which tool to use based on the command
        try:
            # Construct the prompt for the command execution
            prompt = f"""
            Execute the following command on device {device_params.hostname}:
            
            Command: {current_step.command}
            
            Device type: {device_params.device_type}
            
            Select the appropriate tool based on the command type and execute it.
            """
            
            # Run the command executor agent - it will select the appropriate tool
            result = await command_executor_agent.with_deps(deps).arun(prompt)
            
            execution_duration = time.time() - start_time
            
            # Create command output object
            command_output = CommandOutput(
                command=current_step.command,
                raw_output=result,
                status="success",
                execution_time=datetime.now(),
                execution_duration=execution_duration,
                device_hostname=current_state.alert.hostname,
                error_message=None,
                metadata={"simulated": use_simulation}
            )
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            execution_duration = time.time() - start_time
            
            # Create error output
            command_output = CommandOutput(
                command=current_step.command,
                raw_output="",
                status="failure",
                execution_time=datetime.now(),
                execution_duration=execution_duration,
                device_hostname=current_state.alert.hostname,
                error_message=str(e),
                metadata={"simulated": use_simulation}
            )
        
        # Add command output to history
        current_state.command_history.append(command_output)
    else:
        # This is a step without a command to execute
        logger.info(f"Step {current_step.step_number} does not have a command to execute")
        command_output = CommandOutput(
            command="No command",
            raw_output=f"Step {current_step.step_number} did not involve command execution",
            status="success",
            execution_time=datetime.now(),
            execution_duration=0.0,
            device_hostname=current_state.alert.hostname
        )
    
    return {"state": current_state}

# Function to analyze command output
async def analyze_output(state: TroubleshootingGraphState):
    current_state = state["state"]
    action_plan = current_state.action_plan
    current_step_index = action_plan.current_step_index
    
    # Get the current step and its command output
    if not current_state.command_history:
        logger.warning("No command history available for analysis")
        return {"state": current_state}
    
    current_step = action_plan.steps[current_step_index]
    latest_command_output = current_state.command_history[-1]
    
    # Create prompt for analyzing the command output
    prompt = f"""
    Analyze the following command output from a network device:
    
    Device: {latest_command_output.device_hostname}
    Command: {latest_command_output.command}
    
    Output:
    {latest_command_output.raw_output}
    
    This command was executed as part of troubleshooting step #{current_step.step_number}:
    "{current_step.description}"
    
    The expected outcome was:
    "{current_step.expected_outcome}"
    
    Please analyze this output and provide:
    1. A summary of key findings
    2. Any specific issues identified
    3. Specific recommendations based on these findings
    4. A confidence level (0.0-1.0) in your analysis
    
    Format your response in a structured way that can be parsed.
    """
    
    logger.info(f"Analyzing output from command: {latest_command_output.command}")
    
    # Run the output analysis agent
    result = await output_analysis_agent.run(prompt)
    analysis_text = result.data
    
    # Parse the analysis text into a structured result
    analysis_result = await parse_analysis_result(analysis_text)
    
    # Add analysis result to the state
    current_state.analysis_results.append(analysis_result)
    
    return {"state": current_state}

# Function to update the action plan based on analysis
async def update_action_plan(state: TroubleshootingGraphState):
    current_state = state["state"]
    action_plan = current_state.action_plan
    current_step_index = action_plan.current_step_index
    
    # Get the latest analysis result
    if not current_state.analysis_results:
        logger.warning("No analysis results available for updating action plan")
        # Move to the next step without updating the plan
        action_plan.current_step_index += 1
        return {"state": current_state}
    
    latest_analysis = current_state.analysis_results[-1]
    
    # Determine if we need to modify the action plan based on the analysis
    if latest_analysis.confidence_level < 0.5 or not latest_analysis.recommendations:
        # Low confidence or no recommendations, just move to the next step
        logger.info("Low confidence in analysis or no recommendations, continuing with current plan")
        action_plan.current_step_index += 1
        
        # Check if the next step requires human approval
        requires_human_approval = False
        if action_plan.current_step_index < len(action_plan.steps):
            next_step = action_plan.steps[action_plan.current_step_index]
            requires_human_approval = next_step.requires_approval
        
        return {
            "state": current_state,
            "requires_human_approval": requires_human_approval
        }
    
    # Create prompt for updating the action plan
    prompt = f"""
    Based on the following troubleshooting information, update the action plan:
    
    Original Fault Summary:
    {action_plan.fault_summary}
    
    Current Action Plan:
    {action_plan_to_text(action_plan)}
    
    Latest Analysis:
    Summary: {latest_analysis.summary}
    Identified Issues: {', '.join(latest_analysis.identified_issues)}
    Recommendations: {', '.join(latest_analysis.recommendations)}
    Confidence: {latest_analysis.confidence_level}
    
    Current Step Index: {current_step_index}
    
    Please provide an updated action plan based on these findings.
    You can keep the remaining steps as they are, modify them, or add new steps.
    The updated plan should take into account what we've learned from the latest command output.
    
    Return your response in a structured format that I can parse into individual steps.
    """
    
    logger.info("Updating action plan based on latest analysis")
    
    # Run the action plan agent to update the plan
    result = await action_plan_agent.run(prompt)
    updated_plan_text = result.data
    
    # Parse the updated plan
    updated_steps = await parse_action_plan(updated_plan_text)
    
    # Create a new action plan with the updated steps
    # Keep already completed steps and add/modify remaining steps
    completed_steps = action_plan.steps[:current_step_index + 1]
    
    # If we're at the last step and there are more steps in the updated plan, add them
    if current_step_index + 1 >= len(action_plan.steps) and len(updated_steps) > 0:
        new_steps = completed_steps + updated_steps
    else:
        # Otherwise, replace remaining steps with the updated ones
        new_steps = completed_steps + updated_steps
    
    # Create the updated action plan
    updated_action_plan = ActionPlan(
        steps=new_steps,
        current_step_index=current_step_index + 1,  # Move to the next step
        fault_summary=action_plan.fault_summary,
        estimated_completion_time=sum(step.estimated_duration or 0 for step in new_steps),
        requires_manual_intervention=any(step.requires_approval for step in new_steps)
    )
    
    # Update the state with the new action plan
    current_state.action_plan = updated_action_plan
    
    # Check if the next step requires human approval
    requires_human_approval = False
    if updated_action_plan.current_step_index < len(updated_action_plan.steps):
        next_step = updated_action_plan.steps[updated_action_plan.current_step_index]
        requires_human_approval = next_step.requires_approval
    
    return {
        "state": current_state,
        "requires_human_approval": requires_human_approval
    }

# Function to generate the final report
async def generate_final_report(state: TroubleshootingGraphState):
    current_state = state["state"]
    
    # Create prompt for the final report
    prompt = f"""
    Create a final troubleshooting report based on the following information:
    
    Original Alert:
    - Device: {current_state.alert.hostname} (Type: {current_state.alert.device_type})
    - Alert Message: {current_state.alert.alert_message}
    - Severity: {current_state.alert.severity}
    
    Fault Summary:
    {current_state.fault_summary}
    
    Troubleshooting Action Plan:
    {action_plan_to_text(current_state.action_plan)}
    
    Commands Executed:
    {commands_history_to_text(current_state.command_history)}
    
    Analysis Results:
    {analysis_results_to_text(current_state.analysis_results)}
    
    Please provide a comprehensive final report that summarizes:
    1. The original issue and its impact
    2. The troubleshooting steps taken and their outcomes
    3. The root cause identified (if any)
    4. The resolution applied or recommended
    5. Recommendations for preventing similar issues in the future
    
    This report should be suitable for technical management review.
    """
    
    logger.info("Generating final troubleshooting report")
    
    # Run the final report agent
    result = await final_report_agent.run(prompt)
    final_report = result.data
    
    # Update the state with the final report
    current_state.final_report = final_report
    current_state.end_time = datetime.now()
    current_state.status = "completed"
    
    return {"state": current_state}

# Function for handling human approval
async def handle_human_approval(state: TroubleshootingGraphState):
    # This node just returns the current state, waiting for human input
    # The human approval will come through the human_feedback field in the state
    return {"state": state["state"]}

# Function to check if we need human approval
def should_get_human_approval(state: TroubleshootingGraphState):
    if state["requires_human_approval"]:
        return "get_human_approval"
    else:
        return "analyze_output"
    
# Function to check if we're at the end of the action plan
def check_action_plan_completion(state: TroubleshootingGraphState):
    current_state = state["state"]
    action_plan = current_state.action_plan
    
    # Check if we've completed all steps
    if action_plan.current_step_index >= len(action_plan.steps):
        return "generate_final_report"
    else:
        return "execute_action_step"

# Helper function to convert action plan to text
def action_plan_to_text(action_plan: ActionPlan) -> str:
    """Convert an ActionPlan object to a formatted text representation."""
    text = [f"Fault Summary: {action_plan.fault_summary}\n"]
    text.append("Steps:")
    
    for i, step in enumerate(action_plan.steps):
        status = " (Current)" if i == action_plan.current_step_index else ""
        approval = " (Requires Approval)" if step.requires_approval else ""
        text.append(f"{i+1}. {step.description}{status}{approval}")
        if step.command:
            text.append(f"   Command: {step.command}")
        text.append(f"   Expected outcome: {step.expected_outcome}\n")
    
    return "\n".join(text)

# Helper function to convert command history to text
def commands_history_to_text(command_history: List[CommandOutput]) -> str:
    """Convert command history to a formatted text representation."""
    if not command_history:
        return "No commands executed"
    
    text = []
    for i, cmd in enumerate(command_history):
        text.append(f"Command {i+1}: {cmd.command}")
        text.append(f"Status: {cmd.status}")
        text.append(f"Device: {cmd.device_hostname}")
        text.append(f"Time: {cmd.execution_time}")
        text.append(f"Output: \n{cmd.raw_output}\n")
    
    return "\n".join(text)

# Helper function to convert analysis results to text
def analysis_results_to_text(analysis_results: List[AnalysisResult]) -> str:
    """Convert analysis results to a formatted text representation."""
    if not analysis_results:
        return "No analysis results"
    
    text = []
    for i, analysis in enumerate(analysis_results):
        text.append(f"Analysis {i+1}:")
        text.append(f"Summary: {analysis.summary}")
        text.append("Issues Identified:")
        for issue in analysis.identified_issues:
            text.append(f"- {issue}")
        text.append("Recommendations:")
        for rec in analysis.recommendations:
            text.append(f"- {rec}")
        text.append(f"Confidence: {analysis.confidence_level}\n")
    
    return "\n".join(text)

# Helper function to parse action plan text into structured steps
async def parse_action_plan(plan_text: str) -> List[ActionStep]:
    """Parse action plan text into a list of ActionStep objects."""
    # Create a prompt for the LLM to help parse the action plan
    parsing_agent = Agent(
        OpenAIModel(model_name, base_url=base_url, api_key=api_key),
        system_prompt="""
        You are a parser for network troubleshooting action plans. 
        Your job is to convert a textual action plan into a structured format.
        For each step in the plan, extract:
        - step_number (integer)
        - description (string)
        - command (string, or null if no command)
        - expected_outcome (string)
        - requires_approval (boolean)
        - is_service_impacting (boolean)
        - estimated_duration (integer in seconds, or null if unknown)
        
        Return the parsed steps as a JSON-formatted list of objects.
        """
    )
    
    prompt = f"""
    Parse the following network troubleshooting action plan into structured steps:
    
    {plan_text}
    
    Return a JSON array where each object represents one step with the following properties:
    - step_number (integer)
    - description (string)
    - command (string, or null if no command)
    - expected_outcome (string)
    - requires_approval (boolean)
    - is_service_impacting (boolean)
    - estimated_duration (integer in seconds, or null if unknown)
    """
    
    # Run the parsing agent
    result = await parsing_agent.run(prompt)
    
    import json
    try:
        # Try to parse the result as JSON
        steps_data = json.loads(result.data)
        
        # Convert to ActionStep objects
        steps = []
        for step_data in steps_data:
            step = ActionStep(
                step_number=step_data.get("step_number", 1),
                description=step_data.get("description", "Unknown step"),
                command=step_data.get("command"),
                expected_outcome=step_data.get("expected_outcome", "Unknown expected outcome"),
                requires_approval=step_data.get("requires_approval", False),
                is_service_impacting=step_data.get("is_service_impacting", False),
                estimated_duration=step_data.get("estimated_duration")
            )
            steps.append(step)
        
        return steps
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error parsing action plan: {str(e)}")
        # Return a default step if parsing fails
        return [
            ActionStep(
                step_number=1,
                description="Check device status",
                command="show version",
                expected_outcome="Verify device is operational",
                requires_approval=False
            )
        ]

# Helper function to parse analysis result text
async def parse_analysis_result(analysis_text: str) -> AnalysisResult:
    """Parse analysis text into a structured AnalysisResult object."""
    # Create a prompt for the LLM to help parse the analysis
    parsing_agent = Agent(
        OpenAIModel(model_name, base_url=base_url, api_key=api_key),
        system_prompt="""
        You are a parser for network command output analysis. 
        Your job is to convert a textual analysis into a structured format.
        Extract:
        - summary (string)
        - identified_issues (list of strings)
        - recommendations (list of strings)
        - confidence_level (float between 0.0 and 1.0)
        
        Return the parsed analysis as a JSON-formatted object.
        """
    )
    
    prompt = f"""
    Parse the following network command output analysis into a structured format:
    
    {analysis_text}
    
    Return a JSON object with the following properties:
    - summary (string)
    - identified_issues (array of strings)
    - recommendations (array of strings)
    - confidence_level (float between 0.0 and 1.0)
    """
    
    # Run the parsing agent
    result = await parsing_agent.run(prompt)
    
    import json
    try:
        # Try to parse the result as JSON
        analysis_data = json.loads(result.data)
        
        # Convert to AnalysisResult object
        analysis = AnalysisResult(
            summary=analysis_data.get("summary", "No summary provided"),
            identified_issues=analysis_data.get("identified_issues", []),
            recommendations=analysis_data.get("recommendations", []),
            confidence_level=analysis_data.get("confidence_level", 0.5)
        )
        
        return analysis
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error parsing analysis result: {str(e)}")
        # Return a default analysis if parsing fails
        return AnalysisResult(
            summary="Error parsing analysis",
            identified_issues=["Parser failed to extract identified issues"],
            recommendations=["Proceed with caution"],
            confidence_level=0.1
        )

# Build the graph
def build_troubleshooting_graph():
    builder = StateGraph(TroubleshootingGraphState)
    
    # Add nodes
    builder.add_node("generate_fault_summary", generate_fault_summary)
    builder.add_node("generate_action_plan", generate_action_plan)
    builder.add_node("execute_action_step", execute_action_step)
    builder.add_node("analyze_output", analyze_output)
    builder.add_node("update_action_plan", update_action_plan)
    builder.add_node("generate_final_report", generate_final_report)
    builder.add_node("get_human_approval", handle_human_approval)
    
    # Define the edges
    builder.add_edge(START, "generate_fault_summary")
    builder.add_edge("generate_fault_summary", "generate_action_plan")
    builder.add_edge("generate_action_plan", "execute_action_step")
    
    # Conditional edge after executing an action step
    builder.add_conditional_edges(
        "execute_action_step",
        should_get_human_approval,
        {
            "get_human_approval": "get_human_approval",
            "analyze_output": "analyze_output"
        }
    )
    
    # Edge from human approval to analysis
    builder.add_edge("get_human_approval", "analyze_output")
    
    # Edge from analysis to update plan
    builder.add_edge("analyze_output", "update_action_plan")
    
    # Conditional edge after updating the action plan
    builder.add_conditional_edges(
        "update_action_plan",
        check_action_plan_completion,
        {
            "execute_action_step": "execute_action_step",
            "generate_final_report": "generate_final_report"
        }
    )
    
    # Edge from final report to end
    builder.add_edge("generate_final_report", END)
    
    # Configure persistence with memory saver
    memory = MemorySaver()
    
    # Compile the graph
    return builder.compile(checkpointer=memory)

# Function to initialize the troubleshooting workflow with an alert
def initialize_troubleshooting(alert: NetworkAlert) -> TroubleshootingGraphState:
    """Initialize the troubleshooting workflow with a network alert."""
    # Create empty action plan
    action_plan = ActionPlan(
        steps=[],
        fault_summary="",
        current_step_index=0
    )
    
    # Create initial troubleshooting state
    troubleshooting_state = TroubleshootingState(
        alert=alert,
        fault_summary="",
        action_plan=action_plan,
        command_history=[],
        analysis_results=[],
        start_time=datetime.now()
    )
    
    return {
        "state": troubleshooting_state,
        "human_feedback": None,
        "requires_human_approval": False
    }

# Main function to run the troubleshooting workflow
async def run_troubleshooting(alert: NetworkAlert, writer=None):
    """
    Run the troubleshooting workflow for a given network alert.
    
    Args:
        alert: The network alert to troubleshoot
        writer: Optional stream writer function for streaming output
        
    Returns:
        The final troubleshooting state
    """
    # Initialize the state
    initial_state = initialize_troubleshooting(alert)
    
    # Build the graph
    graph = build_troubleshooting_graph()
    
    # If no writer provided, create a simple one
    if writer is None:
        def default_writer(chunk):
            print(chunk, end="", flush=True)
        writer = default_writer
    
    # Generate a unique thread ID for this troubleshooting session
    import uuid
    thread_id = str(uuid.uuid4())
    
    # Configure stream mode
    config = {
        "configurable": {
            "stream_mode": "values" if writer else None,
            "thread_id": thread_id  # Add thread_id to configuration
        }
    }
    
    # Run the graph with streaming
    if writer:
        async for chunk in graph.astream(initial_state, config):
            if isinstance(chunk, dict) and "state" in chunk:
                state_summary = summarize_state(chunk["state"])
                writer(state_summary)
        
        # Get the final result
        final_result = await graph.ainvoke(initial_state, config)
        return final_result["state"]
    else:
        # Run without streaming
        final_result = await graph.ainvoke(initial_state, config)
        return final_result["state"]

# Helper function to provide human approval for a step
async def provide_human_approval(graph, thread_id, approval: bool, feedback: str = ""):
    """
    Provide human approval for a step that requires it.
    
    Args:
        graph: The troubleshooting graph
        thread_id: The thread ID for the current troubleshooting session
        approval: Whether to approve the step
        feedback: Optional feedback about the approval
        
    Returns:
        The updated state
    """
    # Create the human feedback message
    human_feedback = f"{'APPROVED' if approval else 'REJECTED'}: {feedback}"
    
    # Create the input for the graph
    input_data = {"human_feedback": human_feedback}
    
    # Configure the graph
    config = {"configurable": {"thread_id": thread_id}}
    
    # Resume the graph with the human feedback
    result = await graph.acontinue(input_data, config)
    
    return result

# Function to summarize the current state for streaming updates
def summarize_state(state: TroubleshootingState) -> str:
    """Create a summary of the current troubleshooting state for streaming updates."""
    if not state:
        return "Initializing troubleshooting...\n"
    
    summary = []
    summary.append(f"Device: {state.alert.hostname}")
    
    if state.fault_summary:
        summary.append(f"Fault Summary: {state.fault_summary[:100]}...")
    
    if state.action_plan and state.action_plan.steps:
        action_plan = state.action_plan
        current_step_index = action_plan.current_step_index
        
        if current_step_index < len(action_plan.steps):
            current_step = action_plan.steps[current_step_index]
            summary.append(f"Current Step ({current_step_index + 1}/{len(action_plan.steps)}): {current_step.description}")
            
            if current_step.command:
                summary.append(f"Command: {current_step.command}")
        else:
            summary.append("All steps completed")
    
    if state.command_history:
        latest_command = state.command_history[-1]
        summary.append(f"Last Command: {latest_command.command}")
        summary.append(f"Status: {latest_command.status}")
        
        # Add a truncated version of the output
        output_preview = latest_command.raw_output[:100].replace("\n", " ")
        if len(latest_command.raw_output) > 100:
            output_preview += "..."
        summary.append(f"Output: {output_preview}")
    
    if state.analysis_results:
        latest_analysis = state.analysis_results[-1]
        summary.append(f"Analysis: {latest_analysis.summary[:100]}...")
    
    if state.final_report:
        summary.append("Troubleshooting completed")
        summary.append(f"Final Report: {state.final_report[:100]}...")
    
    return "\n".join(summary) + "\n\n"