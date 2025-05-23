from __future__ import annotations as _annotations
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Optional
from pydantic_ai import Agent
from datetime import datetime
from dataclasses import dataclass

from .agent_prompts import FAULT_SUMMARY_SYSTEM_PROMPT
from ..models import FaultSummary

# Load environment variables from .env file
load_dotenv()

class FaultSummaryDependencies(BaseModel):
    """Dependencies for the Fault Summary agent."""
    settings: Dict[str, Any] = {"debug_mode": False, "simulation_mode": True, "test_mode": False}
    logger: Optional[Any] = None

# Initialize the Fault Summary agent with structured output
agent = Agent(
    model='openai:gpt-4.1-mini',
    system_prompt=FAULT_SUMMARY_SYSTEM_PROMPT,
    output_type=FaultSummary,
    retries=2,
    instrument=True,
)

async def run(user_input: str, deps: Optional[FaultSummaryDependencies] = None):
    """
    Run the fault summary agent with the given user input.
    
    Args:
        user_input: The user input describing the network fault alert
        deps: Dependencies for the agent, including settings, logger, and latest_user_message
        
    Returns:
        The agent's response object containing the structured NetworkFaultSummary
    """
    # Initialize dependencies if None
    if deps is None:
        deps = FaultSummaryDependencies()
    
    # Log debug information if debug mode is enabled
    if deps.settings.get("debug_mode", False) and deps.logger:
        deps.logger.info("Fault Summary Agent System Prompt", extra={
            "system_prompt": FAULT_SUMMARY_SYSTEM_PROMPT,
            "user_input": user_input
        })
        
    return await agent.run(user_input, deps=deps)