from __future__ import annotations as _annotations

import logging
from typing import Any
import asyncio
import napalm

from pydantic_ai import RunContext, ModelRetry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("action_executor.agent_tools")

async def execute_cli_commands(ctx: RunContext, commands: list[str]) -> dict:
    """
    Execute CLI commands on a network device using NAPALM.
    
    Takes a list of commands and executes them on the device.
    Note: This tool should only be used when simulation_mode is False.

    Args:
        ctx: The run context containing dependencies (device_driver).
        commands: List of CLI commands to execute.

    Returns:
        A dictionary mapping each command to its output.
    """

    commands = ctx.deps.current_step.commands
    logger.info(f"Executing CLI commands: {commands}")
    
    # Get device driver from dependencies - this is the global NAPALM driver object
    device_driver = ctx.deps.device_driver
    
    results = {}
    errors = []
    
    try:
        # Check if device_driver is None (simulation mode)
        if device_driver is None:
            error_msg = "No valid device driver available. Unable to execute command."
            logger.warning(error_msg)
            for command in commands:
                results[command] = f"ERROR: {error_msg}"
            return results

        # Execute commands using NAPALM
        for command in commands:
            try:                # Use NAPALM's cli method to execute the command
                output = device_driver.cli([command])
                if command in output:
                    results[command] = output[command]
                else:
                    # If the command doesn't match the key in output, log and return all output
                    logger.warning(f"Command '{command}' not found in response keys: {list(output.keys())}")
                    # Take the first value from output as fallback
                    results[command] = list(output.values())[0] if output else "No output received"
            except Exception as e:
                error_msg = f"Error executing command '{command}': {str(e)}"
                logger.error(error_msg)
                results[command] = f"ERROR: {error_msg}"
                errors.append(error_msg)
        
        # If there were errors, log them
        if errors:
            logger.error(f"Encountered {len(errors)} errors while executing commands")
        
        return results
        
    except Exception as e:
        error_msg = f"Unexpected error executing CLI commands: {str(e)}"
        logger.exception(error_msg)
        # Return error for all commands
        for command in commands:
            results[command] = f"ERROR: {error_msg}"
        return results

async def execute_cli_config(ctx: RunContext, commands: list[str]) -> dict:
    """
    Execute configuration commands on a network device using NAPALM.
    
    Uses NAPALM's load_merge_candidate() and commit_config() methods to apply configuration.
    Note: This tool should only be used when simulation_mode is False.

    Args:
        ctx: The run context containing dependencies (device_driver and current_step).

    Returns:
        A dictionary with the config commands as key and success/failure message as value.
    """
    # Get the commands from current_step
    commands = ctx.deps.current_step.commands.copy()
    logger.info(f"Executing config commands: {commands}")
    
    # Get device driver from dependencies - this is the global NAPALM driver object
    device_driver = ctx.deps.device_driver
    
    # Initialize results dictionary
    results = {}
    
    try:
        # Check if device_driver is None (simulation mode)
        if device_driver is None:
            error_msg = "No valid device driver available. Unable to apply configuration."
            logger.warning(error_msg)
            config_str = "\n".join(commands)
            results[config_str] = f"ERROR: {error_msg}"
            return results

        # Check if the first command contains "conf" and remove it if so
        if commands and "conf" in commands[0].lower():
            logger.info(f"Removing configuration mode command: {commands[0]}")
            commands.pop(0)
        
        if not commands:
            logger.warning("No configuration commands to apply after filtering")
            results["No configuration commands"] = "ERROR: No configuration commands to apply"
            return results
            
        # Combine all commands into a single configuration string
        config_str = "\n".join(commands)
        
        try:
            # Load the configuration
            device_driver.load_merge_candidate(config=config_str)
            
            # Check for differences
            diff = device_driver.compare_config()
            if not diff:
                logger.info("No configuration changes detected")
                results[config_str] = "No configuration changes detected"
                return results
                
            # Commit the configuration
            device_driver.commit_config()
            success_msg = "Configuration applied successfully"
            logger.info(success_msg)
            results[config_str] = success_msg
            
        except Exception as e:
            error_msg = f"Error applying configuration: {str(e)}"
            logger.error(error_msg)
            # Try to discard any pending changes
            try:
                device_driver.discard_config()
                logger.info("Discarded pending configuration changes")
            except Exception as discard_error:
                logger.error(f"Error discarding config changes: {str(discard_error)}")
                
            results[config_str] = f"ERROR: {error_msg}"
        
        return results
        
    except Exception as e:
        error_msg = f"Unexpected error executing configuration commands: {str(e)}"
        logger.exception(error_msg)
        config_str = "\n".join(commands)
        results[config_str] = f"ERROR: {error_msg}"
        return results