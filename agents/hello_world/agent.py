from __future__ import annotations as _annotations
import os
from dotenv import load_dotenv
from pydantic_ai import Agent

from .agent_prompts import HELLO_WORLD_SYSTEM_PROMPT

# Load environment variables from .env file
load_dotenv()

# Initialize the Hello World agent
agent = Agent(
    model='openai:gpt-4o',
    system_prompt=HELLO_WORLD_SYSTEM_PROMPT,
    instrument=True,
)

async def run(user_input: str):
    """
    Run the hello world agent with the given user input.
    
    Args:
        user_input: The user's message
        
    Returns:
        The agent's response object
    """
    return await agent.run(user_input)