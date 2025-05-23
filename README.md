# ADAPT

AI-Driven Action Planner & Triage (ADAPT)
(This is a placeholder name - help me find a better one!)

## Overview

ADAPT is an autonomous network troubleshooting system that uses AI-driven agents to diagnose and solve network issues. The system utilizes a multi-agent workflow powered by LangGraph to provide intelligent, step-by-step troubleshooting of network problems.

The workflow consists of the following agents:

1. **Fault Summarizer**: Analyzes network alerts and summarizes the issue
2. **Action Planner**: Creates a detailed troubleshooting plan with specific commands
3. **Action Executor**: Executes commands on network devices (real or simulated)
4. **Action Analyzer**: Analyzes command outputs and determines next steps
5. **Summary Reporter**: Provides a comprehensive troubleshooting report

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Running the Application

Launch the Streamlit application:

```
streamlit run streamlit_app.py
```

## Project Structure

- `agents/`: Directory containing all agent implementations
  - `hello_world/`: Hello World agent implementation
  - `fault_summary/`: Fault Summary agent implementation
  - `action_planner/`: Action Planning agent implementation
  - `action_executor/`: Command execution agent implementation
  - `action_analyzer/`: Output analysis agent implementation
- `configuration/`: Settings and network device inventory
  - `inventory.yml`: Network device inventory
  - `settings.yml`: Application settings
- `graph.py`: LangGraph implementation for the multi-agent workflow
- `streamlit_app.py`: Main Streamlit application
- `tests/`: Test scenarios for simulation mode
- `utils/`: Utility functions and helpers
- `workbench/`: Storage for troubleshooting session logs

## Features

- **Multiple Operation Modes**:
  - **Simulation Mode**: Run commands without actual execution on devices
  - **Test Mode**: Use predefined test data from YAML files
  - **Production Mode**: Connect to and execute commands on real network devices

- **Golden Rules**: Configure safety rules that are always followed by agents

- **Multi-Agent Workflow**: End-to-end troubleshooting using multiple specialized agents

- **Approval System**: Critical commands can be configured to require explicit user approval

- **Individual Agent Testing**: Each agent can be tested independently through the UI

## Contributing

Feel free to contribute by adding new agents or enhancing existing ones.