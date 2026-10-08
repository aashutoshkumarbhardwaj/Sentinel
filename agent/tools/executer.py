from __future__ import annotations

from typing import Any

from agent.reliability.retry import call_with_retry
from agent.tools.registry import (
    ToolRegistry,
    ToolValidationError,
)


class ToolExecutor:
    """
    Execution wrapper for production and simulator tools.
    
    Why: Handles tool schema validation, read-only vs write-action separation,
    and automatic retry logic for transient timeouts via call_with_retry.
    """

    def __init__(self, client: Any):
        self.client = client
        self.registry = ToolRegistry()

    def available_tools(self) -> list[dict[str, Any]]:
        """List schema descriptors for all registered tools."""
        return self.registry.describe()

    def execute(
        self,
        tool: str,
        arguments: dict[str, Any],
    ) -> Any:
        """
        Executes a read-only investigation tool with retry logic.
        
        Enforces that write tools cannot be called directly via execute().
        """
        spec = self.registry.validate(
            tool,
            arguments,
        )

        if not spec.read_only:
            raise ToolValidationError(
                "Write tools must go through the remediation and approval workflow."
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
        """
        Executes a high-risk remediation action post-approval.
        
        Requires non-empty approved_by signature to ensure safety.
        """
        if not approved_by:
            raise PermissionError(
                "Production action requires explicit approval."
            )

        self.registry.validate(
            "execute_action",
            {
                "action": action,
                "target": target,
                "params": params,
                "approved_by": approved_by,
            },
        )

        return self.client.call(
            "execute_action",
            action=action,
            target=target,
            params=params,
            approved_by=approved_by,
        )