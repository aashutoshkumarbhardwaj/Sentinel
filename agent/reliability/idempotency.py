from __future__ import annotations

from typing import Any


def action_key(
    action: str,
    target: str,
    params: dict[str, Any] | None = None,
) -> str:
    return f"{action}:{target}:{params or {}}"


def already_executed(
    actions: list[dict[str, Any]],
    action: str,
    target: str,
    params: dict[str, Any] | None = None,
) -> bool:
    key = action_key(action, target, params)

    return any(
        action_key(
            item.get("action", ""),
            item.get("target", ""),
            item.get("params"),
        )
        == key
        for item in actions
    )