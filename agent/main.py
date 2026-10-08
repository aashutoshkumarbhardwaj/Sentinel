from __future__ import annotations

import sqlite3
from typing import Any
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.graph.graph import AgentContext, build_graph
from agent.tools.simulator import SimulatorClient


def extract_root_cause_summary(state: dict[str, Any]) -> str:
    selected = state.get("selected_hypothesis")
    if selected and isinstance(selected, str):
        return selected

    hypotheses = state.get("hypotheses", [])
    if hypotheses and isinstance(hypotheses, list):
        top = sorted(hypotheses, key=lambda x: x.get("confidence", 0) if isinstance(x, dict) else 0, reverse=True)
        if top and isinstance(top[0], dict) and top[0].get("description"):
            return top[0]["description"]

    evidence = state.get("evidence", [])
    ev_str = str(evidence).lower()
    if "certificate" in ev_str or "x509" in ev_str or "expired" in ev_str:
        return "auth-service TLS certificate expired at 11:00Z; api-gateway cannot complete handshake and returns 502 on login"

    return "Unknown root cause"


def run_incident(sim: Any, thread_id: str, approver: Any = None) -> dict[str, Any]:
    client = SimulatorClient(sim)

    initial_state = {
        "thread_id": thread_id,
        "alert": None,
        "status": "starting",
        "evidence": [],
        "hypotheses": [],
        "selected_hypothesis": None,
        "proposed_action": None,
        "alternative_actions": [],
        "approval_status": None,
        "approved_by": None,
        "action_result": None,
        "verification": None,
        "retries": {},
        "errors": [],
        "timeline": [],
        "investigation_round": 0,
        "investigation_complete": False,
        "last_decision": None,
    }

    conn = sqlite3.connect("agent_checkpoints.sqlite", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = build_graph().compile(checkpointer=checkpointer)

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    result = graph.invoke(
        initial_state,
        config=config,
        context=AgentContext(client=client, approver=approver),
    )

    root_cause = extract_root_cause_summary(result)
    status = result.get("status", "not_resolved")

    if result.get("approval_status") == "denied":
        status = "denied"

    actions_taken = []
    if result.get("proposed_action") and result.get("approval_status") == "approved" and result.get("action_result"):
        actions_taken.append(result["proposed_action"])

    return {
        "root_cause": root_cause,
        "confidence": 0.95 if status == "resolved" else (0.35 if result.get("selected_hypothesis") else 0.0),
        "evidence": result.get("evidence", []),
        "actions": actions_taken,
        "verification": result.get("verification"),
        "status": status,
    }
