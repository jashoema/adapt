from __future__ import annotations as _annotations

import logging
from typing import Any
import asyncio

from pydantic_ai import RunContext, ModelRetry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("action_executor.agent_tools")

async def execute_cli_commands(
    ctx: RunContext, commands: list[str]
) -> str:
    """
    Execute an operational (show) command on a network device.
    
    Connects to the device via SSH and executes the command.
    Note: This tool should only be used when simulation_mode is False.

    Args:
        ctx: The run context containing dependencies (device).
        command: The CLI command to execute.

    Returns:
        The output of the command.
    """


    return "No data available - execute_cli_commands not yet implemented."

    # device: dict = ctx.deps.device.__dict__

    # try:
    #     # Remove any unsafe fields before logging
    #     log_device = device.copy()
    #     log_device.pop("password", None)
    #     log_device.pop("secret", None)
    #     logger.info(f"Establishing SSH connection to {log_device}")

    #     async def _ssh_exec():
    #         conn = ConnectHandler(**device)
    #         if device.get("secret"):
    #             conn.enable()
    #         output = conn.send_command(command)
    #         conn.disconnect()
    #         return output

    #     output = await asyncio.to_thread(_ssh_exec)

    #     return output
    # except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
    #     logger.error(f"Netmiko error: {e}")
    #     raise ModelRetry(f"SSH error: {e}")
    # except Exception as exc:
    #     logger.exception("Unexpected error during SSH connection/command")
    #     raise

async def execute_cli_config(
    ctx: RunContext, commands: list[str]
) -> str:
    """
    Execute configuration commands on a network device.
    
    Connects to the device via SSH and applies the configuration commands.
    Note: This tool should only be used when simulation_mode is False.

    Args:
        ctx: The run context containing dependencies (device).
        commands: List of configuration commands to apply.

    Returns:
        The output of the config commands.
    """

    return "No data available - execute_cli_config not yet implemented."

    # device: dict = ctx.deps.device.__dict__

    # try:
    #     log_device = device.copy()
    #     log_device.pop("password", None)
    #     log_device.pop("secret", None)
    #     logger.info(f"Establishing SSH connection for config to {log_device}")

    #     async def _ssh_exec():
    #         conn = ConnectHandler(**device)
    #         if device.get("secret"):
    #             conn.enable()
    #         output = conn.send_config_set(commands)
    #         conn.disconnect()
    #         return output

    #     output = await asyncio.to_thread(_ssh_exec)

    #     return output
    # except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
    #     logger.error(f"Netmiko error: {e}")
    #     raise ModelRetry(f"SSH error: {e}")
    # except Exception as exc:
    #     logger.exception("Unexpected error during SSH connection/config")
    #     raise