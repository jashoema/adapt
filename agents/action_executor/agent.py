from __future__ import annotations as _annotations

import os
import logging
from dataclasses import dataclass
from typing import Any, List, Dict, Optional, TypedDict

from httpx import AsyncClient
from pydantic_ai import Agent, RunContext, ModelRetry

from .agent_tools import execute_cli_command, execute_cli_config
from .agent_prompts import SYSTEM_PROMPT, TASK_PROMPT
from ..action_planner.agent import TroubleshootingStep

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
    current_action: TroubleshootingStep
    simulation_mode: bool
    device: DeviceCredentials
    client: AsyncClient  # For Pydantic AI usage, potential future tool integration
    debug_mode: bool = False
    logger: Optional[Any] = None

# Main Agent
action_executor = Agent(
    "openai:gpt-4o",
    system_prompt=SYSTEM_PROMPT,
    tools=[execute_cli_command, execute_cli_config],
    deps_type=ActionExecutorDeps,
    output_type=ActionExecutorOutput,
    retries=2,
    name="action_executor",
    description="Network device automation agent that executes CLI commands (e.g. show, config, etc) using SSH or simulation.",
    instrument=True
)

async def run(deps: ActionExecutorDeps, debug_mode: bool = False, logger: Optional[Any] = None) -> RunContext:
    """
    Main agent logic for executing network commands.

    Args:
        deps: The dependencies containing simulation mode and device info.
        debug_mode: Whether to log detailed debugging information
        logger: Optional logger instance to use for logging

    Returns:
        Execution output and status.
    """
    # Update debug_mode and logger in dependencies if provided
    if debug_mode and logger:
        deps.debug_mode = debug_mode
        deps.logger = logger
        
        # Log debug information
        logger.info("Action Executor Agent System Prompt", extra={
            "system_prompt": SYSTEM_PROMPT,
            "task_prompt": TASK_PROMPT
        })
    
    simulation = deps.simulation_mode
    device = deps.device.__dict__
    commands = deps.current_action.command.splitlines()  # Split user input into multiple commands

    for command in commands:
        
        if deps.debug_mode and deps.logger:
            deps.logger.info(f"Executing command", extra={
                "command": command,
                "simulation_mode": simulation,
                "device": device['hostname']
            })

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
    
    if deps.debug_mode and deps.logger:
        deps.logger.info("User prompt for Action Executor", extra={
            "user_prompt": user_prompt
        })
    
    # Execute the agent with the user prompt
    return await action_executor.run(user_prompt, deps=deps)
