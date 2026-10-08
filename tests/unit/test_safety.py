import pytest
from agent.safety.policy import SafetyPolicy, SafetyViolation
from agent.safety.risk import classify_risk


def test_safety_policy_valid_action():
    policy = SafetyPolicy()
    # Valid high risk action during planning stage
    policy.validate(
        action="update_config",
        target="auth-service",
        params={"set": {"tls_cert_ref": "auth-cert-2026-10"}},
        risk="high",
        evidence=["11:00Z cert expired"],
    )


def test_safety_policy_rejects_missing_target():
    policy = SafetyPolicy()
    with pytest.raises(SafetyViolation, match="target is required"):
        policy.validate(
            action="update_config",
            target="",
            params={},
            risk="low",
            evidence=["some evidence"],
        )


def test_safety_policy_rejects_missing_evidence():
    policy = SafetyPolicy()
    with pytest.raises(SafetyViolation, match="requires supporting evidence"):
        policy.validate(
            action="update_config",
            target="auth-service",
            params={},
            risk="low",
            evidence=[],
        )


def test_safety_policy_rejects_disabling_tls():
    policy = SafetyPolicy()
    with pytest.raises(SafetyViolation, match="weaken a security control"):
        policy.validate(
            action="update_config",
            target="api-gateway",
            params={"verify_upstream_tls": False},
            risk="high",
            evidence=["error log"],
        )


def test_risk_classification():
    assert classify_risk("update_config", "auth-service") == "high"
    assert classify_risk("restart_service", "auth-service") == "high"
    assert classify_risk("get_alert", "api-gateway") == "low"
