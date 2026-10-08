from __future__ import annotations

from typing import Any

# Production actions that alter runtime state or topology are classified high risk
HIGH_RISK_ACTIONS = {
    "execute_action",
    "update_config",
    "rollback_deploy",
    "restart_service",
    "scale_service",
    "drain_traffic",
}


def classify_risk(
    action: str,
    target: str,
    params: dict[str, Any] | None = None,
) -> str:
    """
    Classifies risk level of an action ('high' vs 'low').
    
    Why: High risk actions require human approval before execution.
    Read-only investigation tools are low risk; state-modifying actions are high risk.
    """
    if action in HIGH_RISK_ACTIONS:
        return "high"

    return "low"