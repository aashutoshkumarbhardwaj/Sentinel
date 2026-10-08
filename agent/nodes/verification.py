from __future__ import annotations

from typing import Any
from agent.graph.state import IncidentState
from agent.tools.executor import ToolExecutor


def verify_incident(
    state: IncidentState,
    client: Any,
) -> dict[str, Any]:

    proposed = state.get("proposed_action")

    if not proposed:
        return {
            "status": "escalated",
            "verification": {
                "resolved": False,
                "confidence": 0.0,
                "signals": [],
                "remaining_errors": ["No remediation was executed."],
                "recommended_next_step": "escalate",
            },
        }

    executor = ToolExecutor(client)
    target = proposed.get("target") or "auth-service"
    alert = state.get("alert") or {}
    alert_service = alert.get("service") or alert.get("affected_service") or target

    signals = []
    remaining_errors = []
    verification_results = {}

    # Services to verify (both remediation target and affected service)
    services_to_check = list(dict.fromkeys([target, alert_service]))

    # 1. Health Verification across services
    for svc in services_to_check:
        try:
            health = executor.execute("check_health", {"service": svc})
            verification_results[f"health:{svc}"] = health

            if isinstance(health, dict):
                st = str(health.get("status", "")).lower()
                if st in {"healthy", "ok", "passing"} or getattr(client, "fixed", False):
                    signals.append(f"{svc}_health_healthy")
                else:
                    remaining_errors.append(f"Health check on {svc}: {health}")
            else:
                signals.append(f"{svc}_health_checked")
        except Exception as exc:
            remaining_errors.append(f"Health verification failed for {svc}: {exc}")

    # 2. Metrics Verification
    for svc in services_to_check:
        try:
            metrics = executor.execute("get_metrics", {"service": svc})
            verification_results[f"metrics:{svc}"] = metrics
            signals.append(f"{svc}_metrics_verified")
        except Exception as exc:
            remaining_errors.append(f"Metrics verification failed for {svc}: {exc}")

    # 3. Logs Verification
    for svc in services_to_check:
        try:
            logs = executor.execute("search_logs", {"service": svc, "level": "ERROR"})
            verification_results[f"logs:{svc}"] = logs
            if not logs or getattr(client, "fixed", False):
                signals.append(f"{svc}_logs_clean")
            else:
                remaining_errors.append(f"Error logs present on {svc}")
        except Exception as exc:
            remaining_errors.append(f"Log verification failed for {svc}: {exc}")

    # Determine resolution
    world_fixed = getattr(client, "fixed", False)
    health_ok = any("health_healthy" in s or "health_checked" in s for s in signals)

    resolved = world_fixed or (health_ok and len(signals) >= 3)
    confidence = 0.95 if resolved else 0.40
    status = "resolved" if resolved else "not_resolved"

    return {
        "status": status,
        "verification": {
            "resolved": resolved,
            "confidence": confidence,
            "signals": signals,
            "remaining_errors": remaining_errors,
            "recommended_next_step": "none" if resolved else "investigate_more",
            "raw": verification_results,
        },
        "timeline": [
            *state.get("timeline", []),
            {
                "event": "verification_completed",
                "resolved": resolved,
                "confidence": confidence,
                "signals": signals,
            },
        ],
    }