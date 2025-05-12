from __future__ import annotations as _annotations
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal
from pydantic_ai import Agent

from .agent_prompts import FAULT_SUMMARY_SYSTEM_PROMPT

# Load environment variables from .env file
load_dotenv()

# Structured output schema for fault summarization
class FaultSummary(BaseModel):
    """Structured summary of a diagnosed network fault."""
    issue_type: Literal[
        "connectivity", "latency", "packet loss", "DNS", "routing", "hardware failure", "configuration", "other"
    ] = Field(..., description="Identified network issue category")
    most_likely_root_cause: str = Field(..., description="Concise analysis of probable root cause")
    severity: Literal["Critical", "High", "Medium", "Low"] = Field(..., description="Estimated impact and urgency")
    immediate_action_recommendations: str = Field(..., description="Specific, actionable steps to remediate")
    summary: str = Field(..., description="One-sentence technical summary")

# Initialize the Fault Summary agent with structured output
agent = Agent(
    model='openai:gpt-4o',
    system_prompt=FAULT_SUMMARY_SYSTEM_PROMPT,
    output_type=FaultSummary,
    retries=2,
    instrument=True,
)

async def run(user_input: str):
    """
    Run the fault summary agent with the given user input.
    
    Args:
        user_input: The user's description of the network fault
        
    Returns:
        The agent's response object containing the structured FaultSummary
    """
    return await agent.run(user_input)