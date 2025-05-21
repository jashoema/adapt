from __future__ import annotations as _annotations

from typing import Optional, List, Any, Dict
from pydantic import BaseModel
import json

from pydantic_ai import Agent, RunContext

from .agent_prompts import ACTION_ANALYZER_SYSTEM_PROMPT
from ..models import ActionAnalysisReport, ActionExecutorOutput, TroubleshootingStep, FaultSummary

class ActionAnalyzerDependencies(BaseModel):
    """
    Dependencies for the action_analyzer agent.
    
    Attributes:
        action_plan_history: List of previous troubleshooting steps
        action_plan_remaining: List of remaining troubleshooting steps
        current_step_index: Index of the current step in the action plan
        current_step: The current troubleshooting step being executed
        execution_result: The result of the action executor agent
        fault_summary: Summary of the fault being analyzed
        device_facts: Facts about the network device
        settings: Settings for the agent's operation
        logger: Optional logger for debugging and information        
    """
    action_plan_history: List[TroubleshootingStep]
    action_plan_remaining: List[TroubleshootingStep]
    current_step_index: int
    current_step: TroubleshootingStep
    execution_result: ActionExecutorOutput
    fault_summary: FaultSummary
    device_facts: Dict[str, Any]
    settings: Dict[str, Any]
    logger: Optional[Any]
    
# The core agent definition
action_analyzer = Agent(
    model='openai:gpt-4o',  # or use your preferred model
    output_type=ActionAnalysisReport,
    system_prompt=ACTION_ANALYZER_SYSTEM_PROMPT,
    name='action_analyzer',
    retries=1,
    deps_type=ActionAnalyzerDependencies,
    instrument=True,
)

async def run(deps: ActionAnalyzerDependencies) -> RunContext:
    """
    Run the action_analyzer agent to analyze the output of a network device command.
    
    Args:
        deps: The dependencies containing executor output, action plan, fault summary, current step, settings and logger
        
    Returns:
        An ActionAnalysisReport containing structured analysis of the command output
    """
    # Initialize settings if None in dependencies
    if deps.settings is None:
        deps.settings = {"debug_mode": False, "simulation_mode": True}
    
    # Log debug information if debug mode is enabled
    if deps.settings.get("debug_mode", False) and deps.logger:
        deps.logger.info("Action Analyzer Agent System Prompt", extra={
            "system_prompt": ACTION_ANALYZER_SYSTEM_PROMPT
        })
    
    # Extract command output from executor_output
    command_output_context = deps.execution_result.command_outputs
    
    # Manually extract fault_summary fields to avoid datetime serialization issues
    fault_summary_dict = {
        "title": deps.fault_summary.title,
        "summary": deps.fault_summary.summary,
        "hostname": deps.fault_summary.hostname,
        "timestamp": deps.fault_summary.timestamp.isoformat() if deps.fault_summary.timestamp else None,
        "severity": deps.fault_summary.severity,
        "metadata": deps.fault_summary.metadata
    }
    
    # Format the input according to the template
    fault_summary_context = f"fault_summary:\n{json.dumps(fault_summary_dict)}\n\n"
    device_facts_context = f"device_facts:\n{json.dumps(deps.device_facts)}\n\n"
    
    # Add context from the current step being analyzed
    current_step_context = f"current_step:\n{json.dumps(deps.current_step.model_dump())}\n\n"
    errors_context = f"errors:\n{json.dumps(deps.execution_result.errors)}\n\n"
    action_plan_history_context = f"action_plan_history:\n{json.dumps([step.model_dump() for step in deps.action_plan_history])}\n\n"
    action_plan_remaining_context = f"action_plan_remaining:\n{json.dumps([step.model_dump() for step in deps.action_plan_remaining])}\n\n"
    
    # Construct the user input with all relevant context
    user_input = (
        f"command_output: {command_output_context}\n"
        f"errors: {errors_context}\n"
        f"current_step: {current_step_context}\n"
        f"current_step_index: {deps.current_step_index}\n"
        f"max_steps: {deps.settings['max_steps']}\n"
        f"fault_summary: {fault_summary_context}\n"
        f"device_facts: {device_facts_context}\n"
        f"action_plan_history: {action_plan_history_context}\n"
        f"action_plan_remaining: {action_plan_remaining_context}\n"        
    )
    
    if deps.settings.get("debug_mode", False) and deps.logger:
        deps.logger.info("Action Analyzer input", extra={
            "user_input": user_input
        })

    # Run the agent with the formatted input
    return await action_analyzer.run(user_input, deps=deps)
