import asyncio
import os
import json
from dotenv import load_dotenv

# Import agents from their respective packages
from agents.hello_world import run as run_hello_world
from agents.fault_summary import run as run_fault_summary, NetworkFaultSummary
from agents.action_planner import run as run_action_planner

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
    print("3. Network Troubleshooting Planner")
    
    choice = input("Enter choice (1, 2, or 3): ")
    
    if choice == "1":
        user_input = input("You: ")
        result = await run_hello_world(user_input)
        print("Agent:", result.output)  # result.output is the agent's reply
    elif choice == "2":
        print("Describe the network fault alert:")
        user_input = input("You: ")
        result = await run_fault_summary(user_input)
        
        # Pretty print the structured output
        fault_summary = result.output
        print("\nNetwork Fault Alert Summary:")
        print("=" * 60)
        print(f"Alert Title: {fault_summary.title}")
        print(f"Alert Summary: {fault_summary.summary}")
        print(f"Target Device: {fault_summary.hostname}")
        print(f"Operating System: {fault_summary.operating_system}")
        print(f"Timestamp: {fault_summary.timestamp}")
        print(f"Severity: {fault_summary.severity}")
        print("\nOriginal Alert Details:")
        print(json.dumps(fault_summary.original_alert_details, indent=2))
        print("=" * 60)
    elif choice == "3":
        print("Describe the network fault for troubleshooting:")
        user_input = input("You: ")
        result = await run_action_planner(user_input)
        
        # Pretty print the troubleshooting steps
        troubleshooting_steps = result.output
        print("\nNetwork Troubleshooting Plan:")
        print("=" * 60)
        
        for i, step in enumerate(troubleshooting_steps, 1):
            approval_status = "⚠️  REQUIRES APPROVAL" if step.requires_approval else "✓  SAFE TO EXECUTE"
            print(f"\nStep {i}: {step.description}")
            print(f"Status: {approval_status}")
            print(f"\nCommand to execute:")
            print(f"  {step.command}")
            print(f"\nExpected output:")
            print(f"  {step.output_expectation}")
            print("-" * 40)
        
        print("=" * 60)
    else:
        print("Invalid selection. Please run again and select 1, 2, or 3.")

if __name__ == '__main__':
    asyncio.run(main())