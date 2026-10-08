from __future__ import annotations

from typing import Literal

from agent.graph.state import IncidentState


def route_after_investigation(
    state: IncidentState,
) -> Literal[
    "investigate",
    "remediation",
    "end",
]:
    if state.get("status") == "escalated":
        return "end"

    if state.get("investigation_complete"):
        if state.get("selected_hypothesis"):
            return "remediation"
        return "end"

    return "investigate"


def route_after_approval(
    state: IncidentState,
) -> Literal[
    "execute",
    "end",
]:
    if state.get("approval_status") == "approved" or state.get("status") == "approved":
        return "execute"

    return "end"