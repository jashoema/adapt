from __future__ import annotations as _annotations
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Optional
from pydantic_ai import Agent
from datetime import datetime

from .agent_prompts import FAULT_SUMMARY_SYSTEM_PROMPT

# Load environment variables from .env file
load_dotenv()

# Structured output schema for fault summarization
class FaultSummary(BaseModel):
    """Structured summary of a diagnosed network fault alert."""
    title: str = Field(default="Default Title", description="A concise title for the network alert")
    summary: str = Field(default="Unspecified network issue detected", description="A concise summary of the alert")
    hostname: str = Field(default="unknown-device", description="Hostname of the target device")
    operating_system: str = Field(default="Unknown OS", description="Operating system of the target device")
    severity: Literal["Critical", "High", "Medium", "Low"] = Field(default="Medium", description="Estimated impact and urgency")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp when the alert occurred")
    original_alert_details: Dict[str, Any] = Field(default_factory=lambda: {"source": "manual", "details": "No details provided"}, description="Original alert details in JSON format")

# Initialize the Fault Summary agent with structured output
agent = Agent(
    model='openai:gpt-4o',
    system_prompt=FAULT_SUMMARY_SYSTEM_PROMPT,
    output_type=FaultSummary,
    retries=2,
    instrument=True,
)

async def run(user_input: str, debug_mode: bool = False, logger: Optional[Any] = None):
    """
    Run the fault summary agent with the given user input.
    
    Args:
        user_input: The user's description of the network fault
        debug_mode: Whether to log detailed debugging information
        logger: Optional logger instance to use for logging
        
    Returns:
        The agent's response object containing the structured NetworkFaultSummary
    """
    # Log debug information if debug mode is enabled
    if debug_mode and logger:
        logger.info("Fault Summary Agent System Prompt", extra={
            "system_prompt": FAULT_SUMMARY_SYSTEM_PROMPT,
            "user_input": user_input
        })
        
    return await agent.run(user_input)