from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ToolRequest(BaseModel):
    tool: str = Field(..., description="Name of the tool to invoke")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool")
    reason: str = Field(..., description="Justification for invoking this tool based on evidence")
    hypothesis_ids: list[str] = Field(default_factory=list, description="IDs of hypotheses this tool call aims to test")


class HypothesisUpdate(BaseModel):
    hypothesis_id: str = Field(..., description="Identifier of the hypothesis")
    confidence: float = Field(..., description="Updated confidence score between 0.0 and 1.0")
    confidence_change_reason: str = Field(..., description="Reason for updating confidence based on evidence")
    supporting_evidence: list[str] = Field(default_factory=list, description="Evidence item IDs supporting this hypothesis")
    contradicting_evidence: list[str] = Field(default_factory=list, description="Evidence item IDs contradicting this hypothesis")


class InvestigationDecision(BaseModel):
    phase: str = Field(..., description="Current investigation phase (e.g., gather_evidence, select_root_cause, escalate)")
    reasoning: str = Field(..., description="Reasoning behind this decision")
    tool_requests: list[ToolRequest] = Field(default_factory=list, description="Tools requested for gather_evidence phase")
    hypothesis_updates: list[HypothesisUpdate] = Field(default_factory=list, description="Updates to hypotheses confidence and evidence")
    selected_hypothesis: str | None = Field(default=None, description="ID of selected root cause hypothesis if investigation complete")
    confidence: float = Field(default=0.0, description="Overall confidence in selected root cause")
    investigation_complete: bool = Field(default=False, description="True if root cause is identified or investigation escalated")


class ActionCandidate(BaseModel):
    action: str = Field(..., description="Remediation action name (e.g. update_config, rollback_deploy)")
    target: str = Field(..., description="Target service name")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters for the remediation action")
    reason: str = Field(..., description="Why this action will resolve the root cause")
    evidence: list[str] = Field(default_factory=list, description="Evidence supporting this remediation action")
    reversible: bool = Field(default=True, description="Whether this remediation action can be safely reverted")


class RemediationPlan(BaseModel):
    selected_action: ActionCandidate | None = Field(default=None, description="Primary recommended remediation action")
    alternatives: list[ActionCandidate] = Field(default_factory=list, description="Alternative candidate remediation actions")
    rationale: str = Field(..., description="Overall rationale for the selected remediation plan")
    expected_outcome: str = Field(..., description="Expected system behavior after executing the remediation")
