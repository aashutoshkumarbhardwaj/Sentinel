from __future__ import annotations

from typing import Any

from agent.tools.registry import (
    ToolRegistry,
    ToolValidationError,
)
from agent.reliability.retry import call_with_retry


class ToolExecutor:

    def __init__(self, client):
        self.client = client
        self.registry = ToolRegistry()

    def available_tools(self) -> list[dict[str, Any]]:
        return self.registry.describe()

    def execute(
        self,
        tool: str,
        arguments: dict[str, Any],
    ) -> Any:

        spec = self.registry.validate(
            tool,
            arguments,
        )

        if not spec.read_only:
            raise ToolValidationError(
                'Write tools must go through the remediation '
                'and approval workflow.'
            )

        return call_with_retry(
            self.client.call,
            tool,
            **arguments,
        )

    def execute_approved_action(
        self,
        action: str,
        target: str,
        params: dict[str, Any],
        approved_by: str,
    ) -> Any:

        if not approved_by:
            raise PermissionError(
                'Production action requires explicit approval.'
            )

        self.registry.validate(
            'execute_action',
            {
                'action': action,
                'target': target,
                'params': params,
                'approved_by': approved_by,
            },
        )

        return self.client.call(
            'execute_action',
            action=action,
            target=target,
            params=params,
            approved_by=approved_by,
        )