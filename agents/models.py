from dataclasses import dataclass
from typing import Any, List, Dict, Optional, TypedDict, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# DeviceCredentials
class DeviceCredentials:
    hostname: str
    device_type: str
    username: str
    password: str
    port: int = 22
    secret: str | None = None  # For enable/privileged mode
    # Add more fields as required for different device types

# CommandOutput
class CommandOutput(TypedDict):
    cmd: str
    output: str

# ActionExecutorOutput
@dataclass
class ActionExecutorOutput:
    """Output from the action executor agent"""
    description: str  # Description of the action taken
    command_outputs: list[CommandOutput]  # List of command:output pairs
    errors: Optional[List[str]] = None

# ActionAnalysisReport
class ActionAnalysisReport(BaseModel):
    """Structured analysis report for network device command output."""
    analysis: str = Field(..., description="A technical summary (≤120 words)")
    findings: List[str] = Field(..., description="List of line excerpts from the output")
    next_action_type: str = Field(
        ..., 
        description="Next action recommendation", 
        pattern="^(continue|new_action|escalate|resolve)$"
    )
    next_action_reason: str = Field(..., description="1-sentence justification for the next action type")
    updated_action_plan_remaining: Optional[List['TroubleshootingStep']] = Field(
        None, 
        description="Optional list of action steps, included only when next_action_type is 'new_action'"
    )

# TroubleshootingStep
class TroubleshootingStep(BaseModel):
    """
    Represents a single diagnostic step in a network troubleshooting plan.
    Attributes:
        description: A clear explanation of this diagnostic step.
        action_type: The type of action being performed: diagnostic, config, exec, or escalation.
        commands: List of CLI commands to execute (may be empty for escalation type).
        output_expectation: What should be expected in the output and how to interpret it.
        requires_approval: Whether this step may impact configurations or service.
    """
    description: str = Field(..., description="What this step checks or accomplishes")
    action_type: Literal["diagnostic", "config", "exec", "escalation"] = Field(
        ..., description="Type of action: diagnostic, config, exec, or escalation"
    )
    commands: List[str] = Field(
        ..., description="List of CLI commands to execute (may be empty for escalation)"
    )
    output_expectation: str = Field(..., description="What success looks like and how the output is used")
    requires_approval: bool = Field(..., description="True if this step could alter configuration or impact services")
    analysis_report: Optional[ActionAnalysisReport] = Field(..., description="Analysis report of the troubleshooting step; only populated after step has been executed")

# FaultSummary
class FaultSummary(BaseModel):
    """Structured summary of a diagnosed network fault alert."""
    title: str = Field(default="Default Title", description="concise alert title, ≤ 8 words")
    summary: str = Field(default="Unspecified network issue detected", description="≤ 40-word factual synopsis")
    hostname: str = Field(default="unknown-device", description="device hostname")
    timestamp: datetime = Field(default_factory=datetime.now, description="ISO-8601 timestamp")
    severity: Literal["Critical", "High", "Medium", "Low"] = Field(default="Medium", description="Alert severity level")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional diagnostic values like interface names, VRF, module IDs, neighbor IPs")
