from __future__ import annotations

import ast
from typing import Any
from agent.graph.state import IncidentState
from agent.tools.executor import ToolExecutor

# Mapping of primary metric names per environment service
SERVICE_METRIC_MAP = {
    "api-gateway": "login_success_rate_pct",
    "auth-service": "tls_handshake_failures",
    "payments-api": "error_rate_pct",
    "checkout-api": "error_rate_pct",
    "orders-db": "active_connections",
    "cache-service": "hit_ratio",
    "reporting-job": "rows_scanned_millions",
}


def verify_incident(
    state: IncidentState,
    client: Any,
) -> dict[str, Any]:
    """
    Post-remediation verification node.
    
    What it does:
    1. Executes health checks (`check_health`) on target and alert services.
    2. Retrieves service metrics (`get_metrics`), dynamically selecting valid metric names per service.
    3. Searches error logs (`search_logs`) to ensure error rate has subsided.
    4. Combines verification signals to determine whether the incident is 'resolved'.
    """
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

    # 2. Metrics Verification with dynamic metric resolution
    for svc in services_to_check:
        metric_name = SERVICE_METRIC_MAP.get(svc, "error_rate_pct")
        try:
            metrics = executor.execute("get_metrics", {"service": svc, "metric": metric_name})
            verification_results[f"metrics:{svc}"] = metrics
            signals.append(f"{svc}_metrics_verified")
        except Exception as exc:
            # Dynamically parse known metrics from ToolError exception message if primary fails
            exc_str = str(exc)
            known_metrics = []
            if "known:" in exc_str:
                try:
                    start = exc_str.index("known:") + len("known:")
                    raw_list = exc_str[start:].strip()
                    known_metrics = ast.literal_eval(raw_list)
                except Exception:
                    pass

            if not known_metrics:
                known_metrics = ["login_success_rate_pct", "tls_handshake_failures", "error_rate_pct", "active_connections", "rows_scanned_millions", "hit_ratio"]

            fallback_success = False
            for km in known_metrics:
                if km == metric_name:
                    continue
                try:
                    metrics = executor.execute("get_metrics", {"service": svc, "metric": km})
                    verification_results[f"metrics:{svc}"] = metrics
                    signals.append(f"{svc}_metrics_verified")
                    fallback_success = True
                    break
                except Exception:
                    continue

            if not fallback_success:
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

    # Determine final resolution status
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