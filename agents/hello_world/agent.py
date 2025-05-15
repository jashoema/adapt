from __future__ import annotations as _annotations
import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from typing import Any, Dict, Optional
from pydantic import BaseModel

from .agent_prompts import HELLO_WORLD_SYSTEM_PROMPT

# Load environment variables from .env file
load_dotenv()

class HelloWorldDependencies(BaseModel):
    """Dependencies for the Hello World agent."""
    settings: Dict[str, bool] = {"debug_mode": False, "simulation_mode": True}
    logger: Optional[Any] = None

# Initialize the Hello World agent
agent = Agent(
    model='openai:gpt-4o',
    system_prompt=HELLO_WORLD_SYSTEM_PROMPT,
    instrument=True,
)

async def run(user_input: str, deps: Optional[HelloWorldDependencies] = None):
    """
    Run the hello world agent with the given user input.
    
    Args:
        deps: Dependencies for the agent
        
    Returns:
        The agent's response object
    """
    # Initialize dependencies if None
    if deps is None:
        deps = HelloWorldDependencies()
    
    # Log debug information if debug mode is enabled
    if deps.settings.get("debug_mode", False) and deps.logger:
        deps.logger.info("Hello World Agent System Prompt", extra={
            "system_prompt": HELLO_WORLD_SYSTEM_PROMPT,
            "user_input": user_input
        })
        
    return await agent.run(user_input, deps=deps)