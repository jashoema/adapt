import os
from typing import List

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from .agent_prompts import SYSTEM_PROMPT

# Logfire instrumentation is enabled if API key is set
logfire_api_key = os.getenv('LOGFIRE_KEY')
logfire.configure(send_to_logfire='if-token-present')

class TroubleshootingStep(BaseModel):
    """
    Represents a single diagnostic step in a network troubleshooting plan.

    Attributes:
        description: A clear explanation of this diagnostic step.
        command: The exact command to execute (use vendor-appropriate syntax).
        output_expectation: What should be expected in the output and how to interpret it.
        requires_approval: Whether this step may impact configurations or service.
    """
    description: str = Field(..., description="What this diagnostic step checks")
    command: str = Field(..., description="The precise CLI command to execute")
    output_expectation: str = Field(..., description="What to look for in the output and diagnostic implications")
    requires_approval: bool = Field(..., description="True if this step could alter configuration or impact services")

# Create the agent with type-safe output and instructions
action_planner = Agent(
    model="openai:gpt-4o",
    system_prompt=SYSTEM_PROMPT,
    output_type=List[TroubleshootingStep],
    instrument=True,
)

async def run(user_input: str):
    """
    Run the action planner agent with the given user input.
    
    Args:
        user_input: A description of the network fault
        
    Returns:
        The agent's response object containing the list of TroubleshootingStep items
    """
    return await action_planner.run(user_input)

# Add runnable for quick testing
# if __name__ == '__main__':
#     import asyncio

#     async def main():
#         fault_summary = (
#             "Users in VLAN 30 are reporting intermittent connectivity loss to external web resources. "
#             "The issue began after a recent change to core switch routing. The WAN link appears stable."
#         )
#         result = await action_planner.run(fault_summary)
#         for idx, step in enumerate(result.output, 1):
#             print(f"Step {idx}:\n  Description: {step.description}\n  Command: {step.command}\n"
#                   f"  Output Criteria: {step.output_expectation}\n"
#                   f"  Requires Approval: {step.requires_approval}\n")

#     asyncio.run(main())