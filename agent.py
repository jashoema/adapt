from __future__ import annotations as _annotations
import asyncio
import os
from dotenv import load_dotenv

# Import agents from their respective packages
from agents.hello_world import run as run_hello_world
from agents.fault_summary import run as run_fault_summary, NetworkFaultSummary

# Load environment variables from .env file
load_dotenv()

async def main():
    """
    Run a simple main loop for the agents.
    Prompts the user and prints the agent's response.
    """
    print("Select an agent to use:")
    print("1. Hello World Agent")
    print("2. Network Fault Summarization Agent")
    
    choice = input("Enter choice (1 or 2): ")
    
    if choice == "1":
        user_input = input("You: ")
        result = await run_hello_world(user_input)
        print("Agent:", result.output)  # result.output is the agent's reply
    elif choice == "2":
        print("Describe the network fault you're experiencing:")
        user_input = input("You: ")
        result = await run_fault_summary(user_input)
        
        # Pretty print the structured output
        fault_summary = result.output
        print("\nNetwork Fault Analysis:")
        print("=" * 50)
        print(f"Issue Type: {fault_summary.issue_type}")
        print(f"Root Cause: {fault_summary.most_likely_root_cause}")
        print(f"Severity: {fault_summary.severity}")
        print(f"Recommended Actions: {fault_summary.immediate_action_recommendations}")
        print(f"Summary: {fault_summary.summary}")
        print("=" * 50)
    else:
        print("Invalid selection. Please run again and select 1 or 2.")

if __name__ == '__main__':
    asyncio.run(main())