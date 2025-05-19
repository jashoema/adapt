import asyncio
import os
import json
from dotenv import load_dotenv
from dataclasses import dataclass
from httpx import AsyncClient

# Import agents from their respective packages
from agents.hello_world import run as run_hello_world
from agents.hello_world.agent import HelloWorldDependencies
from agents.fault_summary import run as run_fault_summary
from agents.fault_summary.agent import FaultSummary, FaultSummaryDependencies
from agents.action_planner import run as run_action_planner
from agents.action_planner.agent import ActionPlannerDependencies, TroubleshootingStep
from agents.action_executor import run as run_action_executor
from agents.action_executor.agent import DeviceCredentials, ActionExecutorDeps

# Load environment variables from .env file
load_dotenv()

async def main():
    """
    Run a simple main loop for the agents.
    Prompts the user and prints the agent's response.
    """
    # Initialize settings
    settings = {
        "simulation_mode": os.getenv("SIMULATION_MODE", "true").lower() == "true",
        "debug_mode": os.getenv("DEBUG_MODE", "false").lower() == "true"
    }
    
    print("Select an agent to use:")
    print("1. Hello World Agent")
    print("2. Network Fault Summarization Agent")
    print("3. Network Troubleshooting Planner")
    print("4. Network Command Executor")
    
    choice = input("Enter choice (1, 2, 3, or 4): ")
    
    if choice == "1":
        user_input = input("You: ")
        
        # Create dependencies for the hello world agent
        hello_world_deps = HelloWorldDependencies(
            settings=settings
        )
        
        result = await run_hello_world(user_input, deps=hello_world_deps)
        print("Agent:", result.output)  # result.output is the agent's reply
    elif choice == "2":
        print("Describe the network fault alert:")
        user_input = input("You: ")
        
        # Create dependencies for the fault summary agent
        fault_summary_deps = FaultSummaryDependencies(
            settings=settings
        )
        
        result = await run_fault_summary(user_input, deps=fault_summary_deps)
        
        # Pretty print the structured output
        fault_summary = result.output
        print("\nNetwork Fault Alert Summary:")
        print("=" * 60)
        print(f"Alert Title: {fault_summary.title}")
        print(f"Alert Summary: {fault_summary.summary}")
        print(f"Target Device: {fault_summary.hostname}")
        print(f"Timestamp: {fault_summary.timestamp}")
        print(f"Severity: {fault_summary.severity}")
        print("\nOriginal Alert Details:")
        print(json.dumps(fault_summary.metadata, indent=2))
        print("=" * 60)
    elif choice == "3":
        print("Describe the network fault for troubleshooting:")
        user_input = input("You: ")
        
        # Create a new FaultSummary with the user input as the summary
        network_fault_summary = FaultSummary(
            summary=user_input,
            metadata={"source": "user_input", "raw_text": user_input}
        )
        
        # Create dependencies for the action planner
        action_planner_deps = ActionPlannerDependencies(
            fault_summary=network_fault_summary,
            settings=settings
        )
        
        result = await run_action_planner(user_input, deps=action_planner_deps)
        
        # Pretty print the troubleshooting steps
        troubleshooting_steps = result.output
        print("\nNetwork Troubleshooting Plan:")
        print("=" * 60)
        
        for i, step in enumerate(troubleshooting_steps, 1):
            approval_status = "⚠️  REQUIRES APPROVAL" if step.requires_approval else "✓  SAFE TO EXECUTE"
            print(f"\nStep {i}: {step.description}")
            print(f"Status: {approval_status}")
            print(f"\nCommands to execute:")
            if step.commands:
                for cmd in step.commands:
                    print(f"  {cmd}")
            else:
                print("  No commands to execute")
            print(f"\nExpected output:")
            print(f"  {step.output_expectation}")
            print("-" * 40)
        
        print("=" * 60)
    elif choice == "4":
        # Setup for action_executor agent
        simulation_mode = os.getenv("SIMULATION_MODE", "true").lower() == "true"
        mode_display = "SIMULATION" if simulation_mode else "REAL EXECUTION via SSH"
        
        print(f"\nNetwork Command Executor (Running in {mode_display} mode)")
        print(f"Target Device: {os.getenv('DEVICE_HOSTNAME', '192.0.2.100')} ({os.getenv('DEVICE_TYPE', 'cisco_ios')})")
        print("=" * 60)
        print("Enter a command to execute (for config commands with multiple lines, end with CTRL+D):")
        
        # Handle multi-line input for config commands
        user_input = ""
        commands = []
        try:
            user_input = input("Command: ")
            commands.append(user_input)
            
            # Check if this might be a multi-line config command
            if not any(keyword in user_input.lower() for keyword in ["show", "ping", "traceroute"]):
                print("This appears to be a config command. Enter additional commands (CTRL+D to finish):")
                while True:
                    try:
                        line = input("> ")
                        if line:
                            commands.append(line)
                    except EOFError:
                        break
        except EOFError:
            pass
        
        # Setup device credentials from environment variables
        device_credentials = DeviceCredentials(
            hostname=os.getenv("DEVICE_HOSTNAME", "192.0.2.100"),
            device_type=os.getenv("DEVICE_TYPE", "cisco_ios"),
            username=os.getenv("DEVICE_USERNAME", "admin"),
            password=os.getenv("DEVICE_PASSWORD", "password"),
            port=int(os.getenv("DEVICE_PORT", "22")),
            secret=os.getenv("DEVICE_SECRET", None)
        )
        
        # Create a dummy TroubleshootingStep for execution
        action = TroubleshootingStep(
            description="Execute CLI command",
            action_type="diagnostic",
            commands=commands,
            output_expectation="Command should execute successfully",
            requires_approval=False
        )
        
        # Create dependencies with settings included
        deps = ActionExecutorDeps(
            current_action=action,
            simulation_mode=simulation_mode,
            device=device_credentials,
            client=AsyncClient(),
            settings=settings
        )
        
        # Execute the command using action_executor agent
        print("\nExecuting command...")
        result = await run_action_executor(deps=deps)
        
        # Format and display the output based on the updated ActionExecutorOutput structure
        print("\nCommand Execution Result:")
        print("=" * 60)
        print(f"Simulation Mode: {'✅ Yes' if result.output.simulation_mode else '❌ No'}")
        
        print("\nCommand Outputs:")
        print("-" * 60)
        for cmd_output in result.output.command_outputs:
            print(f"Command: {cmd_output['cmd']}")
            print(f"Output:\n{cmd_output['output']}")
            print("-" * 40)
        
        if result.output.errors and len(result.output.errors) > 0:
            print("\nErrors:")
            print("-" * 60)
            for error in result.output.errors:
                print(f"- {error}")
        
        print("=" * 60)
    else:
        print("Invalid selection. Please run again and select 1, 2, 3, or 4.")

if __name__ == '__main__':
    asyncio.run(main())