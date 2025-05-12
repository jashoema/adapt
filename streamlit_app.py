import streamlit as st
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import agents from their respective packages
from agents.hello_world import run as run_hello_world
from agents.fault_summary import run as run_fault_summary
from agents.action_planner import run as run_action_planner

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
        ["Hello World Agent", "Fault Summarizer", "Network Troubleshooting Planner"]
    )

# Display appropriate header and description based on selected agent
if agent_type == "Hello World Agent":
    st.markdown("### 👋 Hello World Agent")
    st.markdown("This is a simple hello-world agent that responds with a friendly greeting.")
elif agent_type == "Fault Summarizer":
    st.markdown("### 🔧 Fault Summarizer")
    st.markdown("Describe a network fault, and this agent will analyze and summarize the issue.")
else:
    st.markdown("### 🔍 Network Troubleshooting Planner")
    st.markdown("Provide a summary of a network fault, and this agent will create a detailed troubleshooting plan with specific commands to execute.")

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
                else:
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
            
            response = asyncio.run(get_response())
            message_placeholder.markdown(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})