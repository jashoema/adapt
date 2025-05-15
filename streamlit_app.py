import streamlit as st
import asyncio
import os
from typing import Dict
from dotenv import load_dotenv
from httpx import AsyncClient
from datetime import datetime
import uuid
import logging

from langgraph.types import Command

# Import the custom StreamlitLogger
from utils.streamlit_logger import get_streamlit_logger

# Create a main logger for the streamlit app
logger = get_streamlit_logger("streamlit_app")

# Load environment variables from .env file
load_dotenv()

# Import agents from their respective packages
from agents.hello_world import run as run_hello_world
from agents.hello_world.agent import HelloWorldDependencies
from agents.fault_summary import run as run_fault_summary
from agents.fault_summary.agent import FaultSummaryDependencies
from agents.action_planner import run as run_action_planner
from agents.action_executor import run as run_action_executor
from agents.action_analyzer import run as run_action_analyzer
from agents.action_executor.agent import DeviceCredentials, ActionExecutorDeps
from agents.action_planner.agent import ActionPlannerDependencies, TroubleshootingStep
from agents.fault_summary.agent import FaultSummary
from agents.action_analyzer.agent import ActionAnalyzerDependencies

# Import the graph for the Multi-Agent workflow
from graph import agentic_flow

# Set page configuration
st.set_page_config(
    page_title="AI Agents Dashboard",
    page_icon="🤖",
    layout="centered"
)


@st.cache_resource
def get_thread_id():
    return str(uuid.uuid4())

thread_id = get_thread_id()

async def run_agent_with_streaming(user_input: str, settings: Dict[str, bool] = None):
    """
    Run the agent with streaming text for the user_input prompt,
    while maintaining the entire conversation in `st.session_state.messages`.
    """
    if settings is None:
        settings = {"simulation_mode": True, "debug_mode": False}
        
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    # First message from user
    if len(st.session_state.messages) == 1:
        async for msg in agentic_flow.astream(
                {"latest_user_message": user_input, "settings": settings}, config, stream_mode="custom"
            ):
                yield msg
    # Continue the conversation
    else:
        async for msg in agentic_flow.astream(
            Command(resume=user_input), config, stream_mode="custom"
        ):
            yield msg

# Initialize settings in session state
if "settings" not in st.session_state:
    st.session_state.settings = {
        "simulation_mode": os.getenv("SIMULATION_MODE", "true").lower() == "true",
        "debug_mode": os.getenv("DEBUG_MODE", "false").lower() == "false"
    }

# Add a title and description
st.title("🤖 AI Agents Dashboard")

# Add sidebar for agent selection
with st.sidebar:
    st.header("Select Agent")
    agent_type = st.radio(
        "Choose an agent:",
        ["Hello World Agent", "Fault Summarizer", "Network Troubleshooting Planner", "Command Executor", "Action Analyzer", "Multi-Agent"]
    )
    
    # Add toggles for settings
    st.header("Settings")
    simulation_mode = st.toggle("Simulation Mode", value=st.session_state.settings["simulation_mode"], help="Enable simulation mode to run commands without actual execution")
    debug_mode = st.toggle("Debug Mode", value=st.session_state.settings["debug_mode"], help="Enable debug mode for additional logging and information")
    
    # Update session state when toggles change
    st.session_state.settings["simulation_mode"] = simulation_mode
    st.session_state.settings["debug_mode"] = debug_mode
    
# Display appropriate header and description based on selected agent
if agent_type == "Hello World Agent":
    st.markdown("### 👋 Hello World Agent")
    st.markdown("This is a simple hello-world agent that responds with a friendly greeting.")
elif agent_type == "Fault Summarizer":
    st.markdown("### 🔧 Fault Summarizer")
    st.markdown("Describe a network fault, and this agent will analyze and summarize the issue.")
elif agent_type == "Network Troubleshooting Planner":
    st.markdown("### 🔍 Network Troubleshooting Planner")
    st.markdown("Provide a summary of a network fault, and this agent will create a detailed troubleshooting plan with specific commands to execute.")
elif agent_type == "Action Analyzer":
    st.markdown("### 📊 Action Analyzer")
    st.markdown("This agent analyzes the output of network commands and provides structured insights, findings, and recommendations.")
    st.info("Enter a network command output to analyze, or paste the full output of a previous command execution.")
elif agent_type == "Multi-Agent":
    st.markdown("### 🔄 Multi-Agent Network Troubleshooter")
    st.markdown("This workflow connects all agents together using LangGraph to provide end-to-end network troubleshooting.")
    st.markdown("Describe a network issue, and the workflow will run through these steps:")
    st.markdown("1. 🔧 **Fault Summary**: Analyze and summarize the issue")
    st.markdown("2. 🔍 **Action Planning**: Create a troubleshooting plan with specific steps")
    st.markdown("3. 🖥️ **Action Execution**: Execute each step of the plan")
    st.markdown("4. 📊 **Action Analysis**: Analyze the output of each step")
    st.info("Currently running in: " + ("SIMULATION mode" if st.session_state.settings["simulation_mode"] else "REAL EXECUTION mode via SSH"))
    
    # Add device info display for Multi-Agent as well
    device_info = {
        "Hostname": os.getenv("DEVICE_HOSTNAME", "192.0.2.100"),
        "Device Type": os.getenv("DEVICE_TYPE", "cisco_ios"),
        "SSH Port": os.getenv("DEVICE_PORT", "22")
    }
    st.sidebar.subheader("Device Information")
    for key, value in device_info.items():
        st.sidebar.text(f"{key}: {value}")
else:
    st.markdown("### 🖥️ Command Executor")
    st.markdown("Enter a network command to execute on a device. The agent will determine if it's an operational or configuration command and execute it appropriately.")
    st.info("Currently running in: " + ("SIMULATION mode" if st.session_state.settings["simulation_mode"] else "REAL EXECUTION mode via SSH"))
    # Add device info display
    device_info = {
        "Hostname": os.getenv("DEVICE_HOSTNAME", "192.0.2.100"),
        "Device Type": os.getenv("DEVICE_TYPE", "cisco_ios"),
        "SSH Port": os.getenv("DEVICE_PORT", "22")
    }
    st.sidebar.subheader("Device Information")
    for key, value in device_info.items():
        st.sidebar.text(f"{key}: {value}")

# Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Reset chat when changing agents
if "current_agent" not in st.session_state or st.session_state.current_agent != agent_type:
    st.session_state.messages = []
    st.session_state.current_agent = agent_type

# Initialize current_response for debug logging
if "current_response" not in st.session_state:
    st.session_state.current_response = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
user_input = st.chat_input("Say something to the agent...")

# Handle user input
if user_input:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Display assistant response with a spinner
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Thinking..."):
            # Get response from the appropriate agent
            async def get_response():
                # Create a logger specific to the current agent
                agent_logger = get_streamlit_logger(f"agent.{agent_type.replace(' ', '_').lower()}")
                
                # Initialize empty response for debug messages to append to
                st.session_state.current_response = ""
                
                if st.session_state.settings["debug_mode"]:
                    logger.info(f"Processing input with {agent_type}", extra={"user_input": user_input})
                
                if agent_type == "Hello World Agent":
                    if st.session_state.settings["debug_mode"]:
                        agent_logger.info("Running Hello World Agent", extra={"user_input": user_input})
                    
                    # Create dependencies for the Hello World agent
                    hello_world_deps = HelloWorldDependencies(
                        settings=st.session_state.settings,
                        logger=agent_logger
                    )
                    
                    # Pass the dependencies to the agent
                    result = await run_hello_world(user_input, deps=hello_world_deps)
                    return result.output
                elif agent_type == "Multi-Agent":
                    if st.session_state.settings["debug_mode"]:
                        agent_logger.info("Running Multi-Agent Workflow", extra={"user_input": user_input})
                    
                    # Create device credentials from environment variables
                    device_hostname = os.getenv("DEVICE_HOSTNAME", "192.0.2.100")
                    device_type = os.getenv("DEVICE_TYPE", "cisco_ios")
                    
                    response_content = ""
                    async for chunk in run_agent_with_streaming(user_input, settings=st.session_state.settings):
                        response_content += chunk
                        # Update the placeholder with the current response content
                        message_placeholder.markdown(response_content)

                    return response_content
                elif agent_type == "Fault Summarizer":
                    if st.session_state.settings["debug_mode"]:
                        agent_logger.info("Running Fault Summarizer Agent", extra={"user_input": user_input})
                    
                    # Create dependencies for the Fault Summarizer agent
                    fault_summary_deps = FaultSummaryDependencies(
                        settings=st.session_state.settings,
                        logger=agent_logger
                    )
                    
                    # Pass dependencies to the agent
                    result = await run_fault_summary(user_input, deps=fault_summary_deps)
                    # Format structured output for display
                    fault_summary = result.output
                    formatted_output = f"""
### Network Fault Alert Summary

**Alert Title:** {fault_summary.title}

**Alert Summary:** {fault_summary.summary}

**Target Device:** {fault_summary.hostname}

**Operating System:** {fault_summary.operating_system}

**Timestamp:** {fault_summary.timestamp}

**Severity:** {fault_summary.severity}

**Original Alert Details (JSON)**

```json
{str(fault_summary.original_alert_details).replace("'", '"')}
```

                    """
                    return formatted_output
                elif agent_type == "Network Troubleshooting Planner":
                    if st.session_state.settings["debug_mode"]:
                        agent_logger.info("Running Network Troubleshooting Planner Agent", extra={"user_input": user_input})
                    
                    # Create a new FaultSummary with the user input as the summary
                    # THIS IS ONLY TEMPORARY until we introduce LangGraph
                    network_fault_summary = FaultSummary(
                        summary=user_input,
                        original_alert_details={"source": "user_input", "raw_text": user_input}
                    )
                    
                    # Create the dependency object
                    action_planner_deps = ActionPlannerDependencies(
                        fault_summary=network_fault_summary,
                        settings=st.session_state.settings,
                        logger=agent_logger
                    )
                    
                    # Call the action planner with the dependencies
                    result = await run_action_planner(user_input, deps=action_planner_deps)
                    action_plan = result.output
                    
                    # Format the troubleshooting steps for display
                    formatted_output = "### Network Troubleshooting Plan\n\n"
                    
                    for i, step in enumerate(action_plan, 1):
                        approval_tag = "⚠️ **Requires Approval**" if step.requires_approval else "✅ **Safe to Execute**"
                        formatted_output += f"## Step {i}: {step.description}\n\n"
                        formatted_output += f"{approval_tag}\n\n"
                        formatted_output += f"**Command:**\n```\n{step.command}\n```\n\n"
                        formatted_output += f"**Expected Output:**\n{step.output_expectation}\n\n"
                        formatted_output += "---\n\n"
                    
                    return formatted_output
                elif agent_type == "Action Analyzer":
                    if st.session_state.settings["debug_mode"]:
                        agent_logger.info("Running Action Analyzer Agent", extra={"user_input": user_input})
                    
                    # For demonstration purposes, use a sample output and dependencies
                    # In a real workflow, these would come from previous steps in the troubleshooting process
                    
                    # Create a simulated command output for the action executor
                    command_output = {
                        "cmd": user_input.splitlines()[0],  # Use the first line of user input as the command
                        "output": user_input  # Use the user input as the command output to analyze
                    }
                    
                    # Create sample dependencies for the analyzer
                    network_fault_summary = FaultSummary(
                        title="Network Interface Analysis",
                        summary="Analyzing network interface performance and errors",
                        hostname="router1.example.com",
                        operating_system="Cisco IOS",
                        severity="Medium",
                        timestamp=datetime.now().isoformat(),
                        original_alert_details={"source": "user_input", "raw_text": "Interface analysis"}
                    )
                    
                    action = TroubleshootingStep(
                        description="Analyze interface statistics",
                        command="show interfaces",
                        output_expectation="Review for errors, bandwidth utilization, and packet loss",
                        requires_approval=False
                    )
                    
                    executor_output = type('ActionExecutorOutput', (), {
                        'command_outputs': [command_output],
                        'simulation_mode': True,
                        'errors': None
                    })
                    
                    # Create the dependency object for the analyzer
                    action_analyzer_deps = ActionAnalyzerDependencies(
                        executor_output=executor_output,
                        action_plan=[action],
                        fault_summary=network_fault_summary,
                        current_step=action,
                        settings=st.session_state.settings,
                        logger=agent_logger
                    )
                    
                    # Call the action analyzer with dependencies
                    result = await run_action_analyzer(deps=action_analyzer_deps)
                    analysis_report = result.output
                    
                    # Format the analysis report for display
                    formatted_output = """### Network Command Output Analysis\n\n"""
                    
                    # Key Findings section
                    formatted_output += "#### 📊 Key Findings\n"
                    for finding in analysis_report.key_findings:
                        formatted_output += f"- {finding}\n"
                    
                    # Issues section
                    formatted_output += "\n#### ⚠️ Issues Identified\n"
                    if analysis_report.issues_identified:
                        for issue in analysis_report.issues_identified:
                            formatted_output += f"- {issue}\n"
                    else:
                        formatted_output += "- No issues identified\n"
                    
                    # Recommendations section
                    formatted_output += "\n#### 📋 Recommendations\n"
                    for recommendation in analysis_report.recommendations:
                        formatted_output += f"- {recommendation}\n"
                    
                    # Confidence level
                    formatted_output += f"\n**Confidence Level:** {analysis_report.confidence_level}\n"
                    
                    return formatted_output
                else:  # Command Executor
                    if st.session_state.settings["debug_mode"]:
                        agent_logger.info("Running Command Executor Agent", extra={"user_input": user_input})
                    
                    # Create device credentials from environment variables
                    device_credentials = DeviceCredentials(
                        hostname=os.getenv("DEVICE_HOSTNAME", "192.0.2.100"),
                        device_type=os.getenv("DEVICE_TYPE", "cisco_ios"),
                        username=os.getenv("DEVICE_USERNAME", "admin"),
                        password=os.getenv("DEVICE_PASSWORD", "password"),
                        port=int(os.getenv("DEVICE_PORT", "22")),
                        secret=os.getenv("DEVICE_SECRET", None)
                    )
                    
                    action = TroubleshootingStep(
                        description="Execute CLI command",
                        command=user_input,
                        output_expectation="Command should execute successfully",
                        requires_approval=False
                    )

                    # Create dependencies for the action executor
                    action_executor_deps = ActionExecutorDeps(
                        current_action=action,
                        simulation_mode=st.session_state.settings["simulation_mode"],
                        device=device_credentials,
                        client=AsyncClient(),
                        settings=st.session_state.settings,
                        logger=agent_logger
                    )
                    
                    # Execute the commands using the action_executor agent
                    result = await run_action_executor(deps=action_executor_deps)
                    
                    result_command_outputs = getattr(result.output,"command_outputs", [{"cmd": "No output", "output": "No output"}])
                    result_simulation_mode = getattr(result.output,"simulation_mode", True)
                    result_errors = getattr(result.output,"errors", [])
                    
                    # Format the output for display based on the updated ActionExecutorOutput structure
                    formatted_output = f"""
### Command Execution Result

**Simulation Mode:** {"Yes" if result_simulation_mode else "No"}

**Command Outputs:**
"""
                    
                    for cmd_output in result_command_outputs:
                        formatted_output += f"""
**Command:** `{cmd_output['cmd']}`

```
{cmd_output['output']}
```
"""
                    
                    if result_errors and len(result_errors) > 0:
                        formatted_output += "\n**Errors:**\n"
                        for error in result_errors:
                            formatted_output += f"- {error}\n"
                    
                    return formatted_output
            
            response = asyncio.run(get_response())
            
            # Reset the current response accumulator
            st.session_state.current_response = None
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})