from __future__ import annotations

from typing import Any


class SafetyViolation(Exception):
    pass


class SafetyPolicy:

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

        if not target:
            raise SafetyViolation(
                "Remediation target is required."
            )

        if not evidence:
            raise SafetyViolation(
                "Remediation requires supporting evidence."
            )

        if check_approval and risk in {"high", "critical"}:
            if not approved_by:
                raise SafetyViolation(
                    "High-risk remediation requires human approval."
                )

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

        serialized = str(params).lower()

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