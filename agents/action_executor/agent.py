from __future__ import annotations as _annotations

import os
import logging
from dataclasses import dataclass
from typing import Any, List, Dict, Optional, TypedDict

from httpx import AsyncClient
from pydantic_ai import Agent, RunContext, ModelRetry

from .agent_tools import execute_cli_command, execute_cli_config
from .agent_prompts import SYSTEM_PROMPT, TASK_PROMPT

import logfire

# configure logfire with API key from environment variable
logfire_api_key = os.getenv('LOGFIRE_TOKEN')
logfire.configure(token=logfire_api_key)
logfire.info('Execution started')
logfire.instrument_openai()


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("action_executor.agent")

@dataclass
class DeviceCredentials:
    hostname: str
    device_type: str
    username: str
    password: str
    port: int = 22
    secret: str | None = None  # For enable/privileged mode
    # Add more fields as required for different device types

class CommandOutput(TypedDict):
    cmd: str
    output: str

@dataclass
class ActionExecutorOutput:
    """Output from the action executor agent"""
    command_outputs: list[CommandOutput]  # List of command:output pairs
    simulation_mode: bool
    errors: Optional[List[str]] = None

@dataclass
class ActionExecutorDeps:
    simulation_mode: bool
    device: DeviceCredentials
    client: AsyncClient  # For Pydantic AI usage, potential future tool integration

# Main Agent
action_executor = Agent(
    "openai:gpt-4o",
    system_prompt=SYSTEM_PROMPT,
    tools=[execute_cli_command, execute_cli_config],
    deps_type=ActionExecutorDeps,
    output_type=ActionExecutorOutput,
    retries=2,
    name="action_executor",
    description="Network device automation agent that executes CLI commands (e.g. show, config, etc) using SSH or simulation."
)

async def run(deps: ActionExecutorDeps, commands: list[str]) -> ActionExecutorOutput:
    """
    Main agent logic for executing network commands.

    Args:
        deps: The dependencies containing simulation mode and device info.
        commands: The CLI commands to execute.

    Returns:
        Execution output and status.
    """
    simulation = deps.simulation_mode
    device = deps.device.__dict__

    for command in commands:
        logger.info(
            f"Executing command. Simulation: {simulation}, Device: {device['hostname']}, Commands: {commands}"
        )

    # Create a more descriptive user prompt to guide the agent about simulation mode
    user_prompt = f"""
    Execute the following commands on the network device:
    
    {commands if commands else "No command provided."}
    
    Device Information:
    - Hostname: {device['hostname']}
    - Device Type: {device['device_type']}
    - Port: {device['port']}
    
    simulation_mode: {simulation}
    
    REMEMBER: If simulation_mode is TRUE, you must generate realistic device output yourself.
    If simulation_mode is FALSE, you should use the appropriate tool to execute commands on the real device.
    """
    
    # Execute the agent with the user prompt
    return await action_executor.run(user_prompt, deps=deps)
