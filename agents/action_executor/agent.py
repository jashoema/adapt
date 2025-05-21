from __future__ import annotations as _annotations

import os
import logging
import json
from dataclasses import dataclass
from typing import Any, List, Dict, Optional, TypedDict

from pydantic_ai import Agent, RunContext, ModelRetry

from .agent_tools import execute_cli_commands, execute_cli_config
from .agent_prompts import SYSTEM_PROMPT
from ..models import DeviceCredentials, CommandOutput, ActionExecutorOutput, TroubleshootingStep

import logfire

# configure logfire with API key from environment variable
logfire_api_key = os.getenv('LOGFIRE_TOKEN')
logfire.configure(token=logfire_api_key)
logfire.info('Execution started')
logfire.instrument_openai()


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("action_executor.agent")

class ActionExecutorDeps:
    current_step: TroubleshootingStep
    device_driver: Dict[str, Any]
    device_facts: Dict[str, Any]
    settings: Dict[str, bool]
    logger: Optional[Any] = None
    
# Main Agent
action_executor = Agent(
    "openai:gpt-4o",
    system_prompt=SYSTEM_PROMPT,
    tools=[execute_cli_commands, execute_cli_config],
    deps_type=ActionExecutorDeps,
    output_type=ActionExecutorOutput,
    retries=2,
    name="action_executor",
    description="Network device automation agent that executes CLI commands (e.g. show, config, etc) using SSH or simulation.",
    instrument=True
)

async def run(deps: ActionExecutorDeps) -> RunContext:
    """
    Main agent logic for executing network commands.

    Args:
        deps: The dependencies containing simulation mode, device info, settings, and logger

    Returns:
        Execution output and status.
    """
    # Initialize settings if None in dependencies
    if deps.settings is None:
        deps.settings = {"debug_mode": False, "simulation_mode": True}
    
    # Log debug information if debug mode is enabled
    if deps.settings.get("debug_mode", False) and deps.logger:
        deps.logger.info("Action Executor Agent System Prompt", extra={
            "system_prompt": SYSTEM_PROMPT
        })
    
    current_step = deps.current_step
    simulation = deps.settings.get("simulation_mode", True)
    device_facts = deps.device_facts

    # Format the input for the user prompt
    formatted_input = f"device_facts:\n{json.dumps(device_facts)}\n\n"
    formatted_input += f"current_step:\n{json.dumps(current_step)}\n\n"
    formatted_input += f"simulation_mode: {simulation}\n\n"

    user_prompt = formatted_input
    
    if deps.settings.get("debug_mode", False) and deps.logger:
        deps.logger.info("User prompt for Action Executor", extra={
            "user_prompt": user_prompt
        })
    
    # Execute the agent with the user prompt
    return await action_executor.run(user_prompt, deps=deps)
