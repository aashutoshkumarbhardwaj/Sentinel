from __future__ import annotations

from typing import Any, TypedDict


class Evidence(TypedDict, total=False):
    id: str
    source: str
    data: Any
    supports: list[str]
    contradicts: list[str]
    timestamp: str


class Hypothesis(TypedDict, total=False):
    id: str
    description: str
    confidence: float
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    next_test: dict[str, Any]


class ProposedAction(TypedDict, total=False):
    action: str
    target: str
    params: dict[str, Any]
    risk: str
    reason: str
    evidence: list[str]
    reversible: bool


class IncidentState(TypedDict, total=False):
    thread_id: str

    alert: dict[str, Any] | None

    status: str

    evidence: list[Evidence]

    hypotheses: list[Hypothesis]

    selected_hypothesis: str | None

    proposed_action: ProposedAction | None

    alternative_actions: list[ProposedAction]

    approval_status: str | None

    approved_by: str | None

    action_result: dict[str, Any] | None

    verification: dict[str, Any] | None

    retries: dict[str, int]

    errors: list[dict[str, Any]]

    timeline: list[dict[str, Any]]

    investigation_round: int

    investigation_complete: bool

    last_decision: dict[str, Any] | None