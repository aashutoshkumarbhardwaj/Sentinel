from __future__ import annotations

from typing import Any, Callable
from langgraph.types import interrupt

from agent.graph.state import IncidentState


def approval_node(
    state: IncidentState,
    approver: Callable[[dict[str, Any]], str | None] | None = None,
) -> dict[str, Any]:

    proposed = state.get("proposed_action")

    if not proposed:
        return {
            "status": "escalated",
            "approval_status": "denied",
            "approved_by": None,
        }

    risk = proposed.get("risk", "low")

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

    if approver is not None:
        response = approver(request)
    else:
        response = interrupt(
            {
                "type": "production_change_approval",
                "request": request,
            }
        )

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