from __future__ import annotations

from typing import Any, Callable
from agent.tools.simulator import ToolError, ToolTimeout

# Maximum number of retry attempts for transient tool timeouts
DEFAULT_MAX_RETRIES = 3


def call_with_retry(
    fn: Callable[..., Any],
    *args: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    **kwargs: Any,
) -> Any:
    """
    Executes a function with retry logic for transient network/tool timeouts.
    
    Why: In production or chaos testing, read tools may time out intermittently.
    We retry ToolTimeout up to max_retries, while letting permanent ToolErrors fail immediately.
    """
    attempts = 0

    while True:
        try:
            return fn(*args, **kwargs)

        except ToolTimeout:
            attempts += 1
            if attempts > max_retries:
                raise

        except ToolError:
            # Permanent tool errors (e.g. invalid arguments) are not retried
            raise