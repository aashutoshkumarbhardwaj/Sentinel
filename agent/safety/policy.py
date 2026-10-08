from __future__ import annotations

from typing import Any


class SafetyViolation(Exception):
    """Exception raised when a proposed action violates production safety rules."""
    pass


class SafetyPolicy:
    """
    Production safety validator.
    
    Why: Prevents automated remediation from executing dangerous, unevidenced,
    or security-weakening actions in production.
    """

    def validate(
        self,
        action: str,
        target: str,
        params: dict[str, Any],
        risk: str,
        evidence: list[str],
        approved_by: str | None = None,
        check_approval: bool = False,
    ) -> None:
        """
        Validates remediation candidate against safety rules.
        
        Checks:
        1. Remediation target must be explicitly specified.
        2. Remediation action must cite supporting evidence.
        3. High/critical risk actions require human approval when check_approval=True.
        4. Security controls (TLS verification, auth settings) must not be weakened.
        """
        if not target:
            raise SafetyViolation("Remediation target is required.")

        if not evidence:
            raise SafetyViolation("Remediation requires supporting evidence.")

        if check_approval and risk in {"high", "critical"}:
            if not approved_by:
                raise SafetyViolation("High-risk remediation requires human approval.")

        self._validate_security_controls(
            action,
            target,
            params,
        )

    def _validate_security_controls(
        self,
        action: str,
        target: str,
        params: dict[str, Any],
    ) -> None:
        """Scan parameter strings for dangerous security-weakening patterns."""
        serialized = str(params).lower()

        # Dangerous patterns that weaken production security
        dangerous_patterns = (
            "disable_tls",
            "verify_upstream_tls=false",
            "verify_upstream_tls': false",
            "verify_tls=false",
            "verify_tls': false",
            "disable_auth",
            "disable_authentication",
            "disable_security",
        )

        for pattern in dangerous_patterns:
            if pattern in serialized:
                raise SafetyViolation(
                    "Remediation attempts to weaken a security control."
                )