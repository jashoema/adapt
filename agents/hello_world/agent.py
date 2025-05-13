from __future__ import annotations as _annotations
import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from typing import Any, Optional

from .agent_prompts import HELLO_WORLD_SYSTEM_PROMPT

# Load environment variables from .env file
load_dotenv()

# Initialize the Hello World agent
agent = Agent(
    model='openai:gpt-4o',
    system_prompt=HELLO_WORLD_SYSTEM_PROMPT,
    instrument=True,
)

async def run(user_input: str, debug_mode: bool = False, logger: Optional[Any] = None):
    """
    Run the hello world agent with the given user input.
    
    Args:
        user_input: The user's message
        debug_mode: Whether to log detailed debugging information
        logger: Optional logger instance to use for logging
        
    Returns:
        The agent's response object
    """
    # Log debug information if debug mode is enabled
    if debug_mode and logger:
        logger.info("Hello World Agent System Prompt", extra={
            "system_prompt": HELLO_WORLD_SYSTEM_PROMPT,
            "user_input": user_input
        })
        
    return await agent.run(user_input)