from __future__ import annotations

from agent.graph.state import IncidentState
from agent.llm import get_decision_engine
from agent.safety.policy import SafetyPolicy
from agent.safety.risk import classify_risk


def plan_remediation(
    state: IncidentState,
) -> dict:
    """
    Remediation planning node.
    
    What it does:
    1. Invokes decision engine to construct a minimal remediation action supported by evidence.
    2. Classifies action risk (e.g. high risk for production config/deploy modifications).
    3. Validates proposed plan against SafetyPolicy (checking for forbidden patterns like disabling TLS).
    4. Sets status to 'awaiting_approval' for human-in-the-loop review.
    """
    engine = get_decision_engine()

    # Plan candidate action from identified root cause and evidence
    plan = engine.plan_remediation(dict(state))

    if plan.selected_action is None:
        return {
            "status": "escalated",
            "proposed_action": None,
            "alternative_actions": [],
            "timeline": [
                *state.get("timeline", []),
                {
                    "event": "remediation_planning_failed",
                    "reason": plan.rationale,
                },
            ],
        }

    candidate = plan.selected_action

    # Classify action risk level
    risk = classify_risk(
        candidate.action,
        candidate.target,
        candidate.params,
    )

    # Validate against production safety policy
    policy = SafetyPolicy()
    policy.validate(
        action=candidate.action,
        target=candidate.target,
        params=candidate.params,
        risk=risk,
        evidence=candidate.evidence,
    )

    proposed_action = {
        "action": candidate.action,
        "target": candidate.target,
        "params": candidate.params,
        "risk": risk,
        "reason": candidate.reason,
        "evidence": candidate.evidence,
        "reversible": candidate.reversible,
    }

    alternatives = []
    for alternative in plan.alternatives:
        alternatives.append(
            {
                "action": alternative.action,
                "target": alternative.target,
                "params": alternative.params,
                "risk": classify_risk(
                    alternative.action,
                    alternative.target,
                    alternative.params,
                ),
                "reason": alternative.reason,
                "evidence": alternative.evidence,
                "reversible": alternative.reversible,
            }
        )

    return {
        "proposed_action": proposed_action,
        "alternative_actions": alternatives,
        "status": "awaiting_approval",
        "timeline": [
            *state.get("timeline", []),
            {
                "event": "remediation_proposed",
                "action": candidate.action,
                "target": candidate.target,
                "risk": risk,
                "reason": candidate.reason,
            },
        ],
    }