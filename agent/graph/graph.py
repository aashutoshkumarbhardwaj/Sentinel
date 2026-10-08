from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from agent.graph.routing import route_after_approval, route_after_investigation
from agent.graph.state import IncidentState
from agent.nodes.approval import approval_node
from agent.nodes.execution import execute_remediation
from agent.nodes.investigation import investigate_node
from agent.nodes.remediation import plan_remediation
from agent.nodes.verification import verify_incident
from agent.tools.simulator import SimulatorClient


@dataclass
class AgentContext:
    client: SimulatorClient
    approver: Callable[[dict[str, Any]], str | None] | None = None


def load_incident(
    state: IncidentState,
    runtime: Runtime[AgentContext],
):
    client = runtime.context.client

    try:
        alert = client.call("get_alert")
        return {
            "alert": alert,
            "status": "investigating",
            "timeline": [
                *state.get("timeline", []),
                {
                    "event": "incident_loaded",
                    "alert": alert,
                },
            ],
        }
    except Exception as exc:
        return {
            "status": "escalated",
            "errors": [
                *state.get("errors", []),
                {
                    "tool": "get_alert",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
            ],
        }


def investigate(
    state: IncidentState,
    runtime: Runtime[AgentContext],
):
    return investigate_node(
        state,
        runtime.context.client,
    )


def approval(
    state: IncidentState,
    runtime: Runtime[AgentContext],
):
    approver_fn = runtime.context.approver if runtime and hasattr(runtime, "context") and runtime.context else None
    return approval_node(state, approver=approver_fn)


def execute(
    state: IncidentState,
    runtime: Runtime[AgentContext],
):
    return execute_remediation(
        state,
        runtime.context.client,
    )


def verification(
    state: IncidentState,
    runtime: Runtime[AgentContext],
):
    return verify_incident(
        state,
        runtime.context.client,
    )


def build_graph():
    builder = StateGraph(
        IncidentState,
        context_schema=AgentContext,
    )

    builder.add_node("load_incident", load_incident)
    builder.add_node("investigate", investigate)
    builder.add_node("remediation", plan_remediation)
    builder.add_node("approval", approval)
    builder.add_node("execute", execute)
    builder.add_node("verification", verification)

    builder.add_edge(START, "load_incident")
    builder.add_edge("load_incident", "investigate")

    builder.add_conditional_edges(
        "investigate",
        route_after_investigation,
        {
            "investigate": "investigate",
            "remediation": "remediation",
            "end": END,
        },
    )

    builder.add_edge("remediation", "approval")

    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "execute": "execute",
            "end": END,
        },
    )

    builder.add_edge("execute", "verification")
    builder.add_edge("verification", END)

    return builder