from __future__ import annotations

from typing import Any, Callable

from agent.tools.simulator import ToolTimeout, ToolError


DEFAULT_MAX_RETRIES = 3


def call_with_retry(
    fn: Callable[..., Any],
    *args: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    **kwargs: Any,
) -> Any:
    attempts = 0

    while True:
        try:
            return fn(*args, **kwargs)

        except ToolTimeout:
            attempts += 1

            if attempts > max_retries:
                raise

        except ToolError:
            # ToolError may represent a permanent failure.
            # Do not blindly retry every tool error.
            raise