from __future__ import annotations

from typing import Any


HIGH_RISK_ACTIONS = {
    'execute_action',
    'update_config',
    'rollback_deploy',
    'restart_service',
    'scale_service',
    'drain_traffic',
}


def classify_risk(
    action: str,
    target: str,
    params: dict[str, Any] | None = None,
) -> str:

    if action in HIGH_RISK_ACTIONS:
        return 'high'

    return 'low'