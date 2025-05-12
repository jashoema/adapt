import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from httpx import AsyncClient

# Load environment variables from .env file
load_dotenv()

# Import agents from their respective packages
from agents.hello_world import run as run_hello_world
from agents.fault_summary import run as run_fault_summary
from agents.action_planner import run as run_action_planner
from agents.action_executor import run as run_action_executor
from agents.action_executor.agent import DeviceCredentials, ActionExecutorDeps

# Set page configuration
st.set_page_config(
    page_title="AI Agents Dashboard",
    page_icon="🤖",
    layout="centered"
)

# Add a title and description
st.title("🤖 AI Agents Dashboard")

# Add sidebar for agent selection
with st.sidebar:
    st.header("Select Agent")
    agent_type = st.radio(
        "Choose an agent:",
        ["Hello World Agent", "Fault Summarizer", "Network Troubleshooting Planner", "Command Executor"]
    )

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
else:
    st.markdown("### 🖥️ Command Executor")
    st.markdown("Enter a network command to execute on a device. The agent will determine if it's an operational or configuration command and execute it appropriately.")
    st.info("Currently running in: " + ("SIMULATION mode" if os.getenv("SIMULATION_MODE", "true").lower() == "true" else "REAL EXECUTION mode via SSH"))
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
                if agent_type == "Hello World Agent":
                    result = await run_hello_world(user_input)
                    return result.output
                elif agent_type == "Fault Summarizer":
                    result = await run_fault_summary(user_input)
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
                    result = await run_action_planner(user_input)
                    troubleshooting_steps = result.output
                    
                    # Format the troubleshooting steps for display
                    formatted_output = "### Network Troubleshooting Plan\n\n"
                    
                    for i, step in enumerate(troubleshooting_steps, 1):
                        approval_tag = "⚠️ **Requires Approval**" if step.requires_approval else "✅ **Safe to Execute**"
                        formatted_output += f"## Step {i}: {step.description}\n\n"
                        formatted_output += f"{approval_tag}\n\n"
                        formatted_output += f"**Command:**\n```\n{step.command}\n```\n\n"
                        formatted_output += f"**Expected Output:**\n{step.output_expectation}\n\n"
                        formatted_output += "---\n\n"
                    
                    return formatted_output
                else:  # Command Executor
                    # Create device credentials from environment variables
                    device_credentials = DeviceCredentials(
                        hostname=os.getenv("DEVICE_HOSTNAME", "192.0.2.100"),
                        device_type=os.getenv("DEVICE_TYPE", "cisco_ios"),
                        username=os.getenv("DEVICE_USERNAME", "admin"),
                        password=os.getenv("DEVICE_PASSWORD", "password"),
                        port=int(os.getenv("DEVICE_PORT", "22")),
                        secret=os.getenv("DEVICE_SECRET", None)
                    )
                    
                    # Create dependencies for the action executor
                    deps = ActionExecutorDeps(
                        simulation_mode=os.getenv("SIMULATION_MODE", "true").lower() == "true",
                        device=device_credentials,
                        client=AsyncClient()
                    )
                    
                    # Execute the commands using the action_executor agent
                    result = await run_action_executor(
                        deps=deps,
                        commands=user_input.splitlines()  # Split user input into multiple commands
                    )

                    result_command_outputs = getattr(result.output,"command_outputs", [{"cmd": "No output", "output": "No output"}])
                    simulation_mode = getattr(result.output,"simulation_mode", True)
                    result_errors = getattr(result.output,"errors", [])
                    
                    # Format the output for display based on the updated ActionExecutorOutput structure
                    formatted_output = f"""
### Command Execution Result

**Simulation Mode:** {"Yes" if simulation_mode else "No"}

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
            message_placeholder.markdown(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})