from __future__ import annotations

from typing import Any


def record_error(
    errors: list[dict[str, Any]],
    tool: str,
    error_type: str,
    message: str,
    attempt: int,
) -> list[dict[str, Any]]:
    return [
        *errors,
        {
            "tool": tool,
            "error_type": error_type,
            "message": message,
            "attempt": attempt,
        },
    ]