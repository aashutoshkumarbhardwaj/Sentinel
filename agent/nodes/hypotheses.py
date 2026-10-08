from __future__ import annotations

from typing import Any

from agent.graph.state import IncidentState


def create_initial_hypotheses(
    state: IncidentState,
) -> IncidentState:
    alert = state.get("alert") or {}

    hypotheses = [
        {
            "id": "hypothesis_1",
            "description": "A recent deployment introduced or exposed the incident.",
            "confidence": 0.33,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "next_test": {
                "purpose": "Inspect recent deployments for affected services."
            },
        },
        {
            "id": "hypothesis_2",
            "description": "A dependency or infrastructure component is causing the failure.",
            "confidence": 0.33,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "next_test": {
                "purpose": "Inspect service health, metrics, and error logs."
            },
        },
        {
            "id": "hypothesis_3",
            "description": "A configuration or credential has become invalid or expired.",
            "confidence": 0.34,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "next_test": {
                "purpose": "Inspect relevant service configuration."
            },
        },
    ]

    timeline = list(state.get("timeline", []))

    timeline.append(
        {
            "event": "hypotheses_created",
            "details": {
                "count": len(hypotheses),
            },
        }
    )

    return {
        **state,
        "hypotheses": hypotheses,
        "timeline": timeline,
        "status": "hypothesis_generation",
    }


def update_hypothesis_confidence(
    hypothesis: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:

    confidence = float(
        hypothesis.get("confidence", 0.0)
    )

    supports = evidence.get("supports", [])
    contradicts = evidence.get("contradicts", [])

    if hypothesis["id"] in supports:
        confidence += 0.15

    if hypothesis["id"] in contradicts:
        confidence -= 0.15

    confidence = max(
        0.0,
        min(1.0, confidence),
    )

    return {
        **hypothesis,
        "confidence": round(confidence, 3),
    }


def rank_hypotheses(
    state: IncidentState,
) -> IncidentState:

    hypotheses = sorted(
        state.get("hypotheses", []),
        key=lambda h: h.get("confidence", 0.0),
        reverse=True,
    )

    selected = (
        hypotheses[0]["id"]
        if hypotheses
        else None
    )

    return {
        **state,
        "hypotheses": hypotheses,
        "selected_hypothesis": selected,
    }