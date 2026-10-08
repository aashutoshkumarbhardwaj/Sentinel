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
    """
    Conditional routing function evaluated after each investigation round.
    
    Logic:
    - If status is escalated (insufficient evidence or round limit), terminate graph.
    - If investigation is complete and root cause hypothesis selected, proceed to remediation planning.
    - Otherwise, loop back for another round of evidence collection.
    """
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
    """
    Conditional routing function evaluated after the human approval node.
    
    Logic:
    - If approval was granted, proceed to remediation execution.
    - If approval was denied, immediately terminate graph to guarantee safety (0 unapproved actions).
    """
    if state.get("approval_status") == "approved" or state.get("status") == "approved":
        return "execute"

    return "end"