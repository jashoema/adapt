# ADAPT

AI-Driven Action Planner & Troubleshooter (ADAPT)

## Requirements

- Needs Python 3.12 and above

## Overview

ADAPT is an autonomous network troubleshooting system that uses AI-driven agents to diagnose and solve network issues. The system utilizes a multi-agent workflow powered by LangGraph to provide intelligent, step-by-step troubleshooting of network problems.

The workflow consists of the following AI agents:

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
- `static/`: Directory for files served via direct URLs
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

- **Direct Result Access**: Troubleshooting results and response logs are saved as files with direct URL links for easy access and integration with other systems

- **Multi-Agent Workflow**: End-to-end troubleshooting using multiple specialized agents

- **Approval System**: Critical commands can be configured to require explicit user approval

- **Individual Agent Testing**: Each agent can be tested independently through the UI

## Roadmap and Known Issues

See the [CHANGELOG.md](./CHANGELOG.md) for a list of known issues and planned improvements for upcoming releases.

## Contributing

We welcome contributions to ADAPT! Here's how you can contribute:

1. **Fork the repository** on GitHub
2. **Create a branch** for your changes
3. **Make your changes** (new agents, bug fixes, documentation, etc.)
4. **Submit a pull request** back to the main repository

For questions or suggestions, please open an issue on GitHub.

