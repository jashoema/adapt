from __future__ import annotations as _annotations
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Optional
from pydantic_ai import Agent
from datetime import datetime
from dataclasses import dataclass


from .agent_prompts import FAULT_SUMMARY_SYSTEM_PROMPT

# Load environment variables from .env file
load_dotenv()

# Structured output schema for fault summarization
@dataclass
class FaultSummary(BaseModel):
    """Structured summary of a diagnosed network fault alert."""
    title: str = Field(default="Default Title", description="A concise title for the network alert")
    summary: str = Field(default="Unspecified network issue detected", description="A concise summary of the alert")
    hostname: str = Field(default="unknown-device", description="Hostname of the target device")
    operating_system: str = Field(default="Unknown OS", description="Operating system of the target device")
    severity: Literal["Critical", "High", "Medium", "Low"] = Field(default="Medium", description="Estimated impact and urgency")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp when the alert occurred")
    original_alert_details: Dict[str, Any] = Field(default_factory=lambda: {"source": "manual", "details": "No details provided"}, description="Original alert details in JSON format")

class FaultSummaryDependencies(BaseModel):
    """Dependencies for the Fault Summary agent."""
    settings: Dict[str, Any] = {"debug_mode": False, "simulation_mode": True, "test_mode": False}
    logger: Optional[Any] = None

# Initialize the Fault Summary agent with structured output
agent = Agent(
    model='openai:gpt-4o',
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