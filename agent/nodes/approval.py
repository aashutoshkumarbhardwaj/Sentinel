from __future__ import annotations

from typing import Any, Callable
from langgraph.types import interrupt

from agent.graph.state import IncidentState


def approval_node(
    state: IncidentState,
    approver: Callable[[dict[str, Any]], str | None] | None = None,
) -> dict[str, Any]:
    """
    Human-in-the-loop approval gate node.
    
    What it does:
    1. Checks proposed action risk. Low risk actions bypass approval.
    2. High/critical risk actions invoke human approver callback or LangGraph interrupt.
    3. If approved, sets approval_status='approved' and records approved_by identity.
    4. If denied, sets approval_status='denied' and status='denied' (causing graph to halt safely).
    """
    proposed = state.get("proposed_action")

    if not proposed:
        return {
            "status": "escalated",
            "approval_status": "denied",
            "approved_by": None,
        }

    risk = proposed.get("risk", "low")

    # Low risk actions do not require explicit human approval
    if risk not in {"high", "critical"}:
        return {
            "approval_status": "not_required",
            "approved_by": None,
            "status": "approved",
            "timeline": [
                *state.get("timeline", []),
                {
                    "event": "approval_not_required",
                    "risk": risk,
                },
            ],
        }

    request = {
        "action": proposed.get("action"),
        "target": proposed.get("target"),
        "risk": risk,
        "params": proposed.get("params", {}),
        "reason": proposed.get("reason"),
        "evidence": proposed.get("evidence", []),
    }

    # Use runtime approver callback if provided; fallback to LangGraph interrupt
    if approver is not None:
        response = approver(request)
    else:
        response = interrupt(
            {
                "type": "production_change_approval",
                "request": request,
            }
        )

    # Handle denied approval
    if not response:
        return {
            "approval_status": "denied",
            "approved_by": None,
            "status": "denied",
            "timeline": [
                *state.get("timeline", []),
                {
                    "event": "approval_denied",
                    "action": proposed.get("action"),
                    "target": proposed.get("target"),
                },
            ],
        }

    approved_by = (
        response
        if isinstance(response, str)
        else response.get("approved_by")
    )

    if not approved_by:
        return {
            "approval_status": "denied",
            "approved_by": None,
            "status": "denied",
            "timeline": [
                *state.get("timeline", []),
                {
                    "event": "approval_denied",
                    "action": proposed.get("action"),
                    "target": proposed.get("target"),
                },
            ],
        }

    # Grant approval
    return {
        "approval_status": "approved",
        "approved_by": approved_by,
        "status": "approved",
        "timeline": [
            *state.get("timeline", []),
            {
                "event": "approval_granted",
                "approved_by": approved_by,
                "action": proposed.get("action"),
                "target": proposed.get("target"),
            },
        ],
    }