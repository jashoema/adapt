# Archon MCP Test

A demonstration project for AI agents built using the Model Context Protocol (MCP) framework.

## Overview

This repository contains a collection of AI agents implemented with the Model Context Protocol. Currently, the project includes:

- **Hello World Agent**: A simple demonstration agent that responds with greetings
- **Fault Summary Agent**: An agent that analyzes and summarizes network faults

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
- `streamlit_app.py`: Main Streamlit application

## Contributing

Feel free to contribute by adding new agents or enhancing existing ones.