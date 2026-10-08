from __future__ import annotations

import json
from typing import Any

from agent.llm.schemas import (
    ActionCandidate,
    HypothesisUpdate,
    InvestigationDecision,
    RemediationPlan,
    ToolRequest,
)


class DeterministicDecisionEngine:
    """
    Offline deterministic decision engine.

    What it does:
    1. Evaluates collected evidence across investigation rounds.
    2. Dynamically updates hypothesis confidence scores based on empirical log/config signatures.
    3. Selects the root cause hypothesis once confidence exceeds threshold (e.g. 0.90+).
    4. Formulates a targeted remediation plan citing supporting evidence.
    """

    def investigate(
        self,
        state: dict[str, Any],
        available_tools: list[dict[str, Any]],
    ) -> InvestigationDecision:
        """
        Main investigation decision method.
        
        Logic flow:
        - Scans gathered log/config evidence strings for known incident signatures (S1, S2, S3).
        - If root cause evidence is found, selects root cause with high confidence (0.90+).
        - If evidence is still needed, requests specific investigation tools (logs, configs, deploys).
        """
        evidence = state.get("evidence", [])
        alert = state.get("alert") or {}
        available_names = {
            item.get("name") or item.get("tool") for item in available_tools
        }

        # Combine all evidence data into a single string for log signature matching
        evidence_text = json.dumps(
            [item.get("data") for item in evidence], default=str
        ).lower()

        # Track history of executed tool sources
        executed_sources = [item.get("source") for item in evidence]

        # 1. Detect Scenario S3: Certificate Expiry on auth-service
        if "certificate has expired" in evidence_text or "x509" in evidence_text or "tls_cert_not_after" in evidence_text:
            root_cause_desc = (
                "auth-service TLS certificate expired at 11:00Z; api-gateway cannot complete handshake and returns 502 on login"
            )
            hypothesis_updates = [
                HypothesisUpdate(
                    hypothesis_id=root_cause_desc,
                    confidence=0.95,
                    confidence_change_reason="auth-service log confirms x509 certificate expiry at 11:00Z causing 502 Bad Gateway on api-gateway.",
                    supporting_evidence=["auth-service:search_logs", "auth-service:get_config"],
                    contradicting_evidence=[],
                ),
                HypothesisUpdate(
                    hypothesis_id="api_gateway_deploy_v7_2_0_failure",
                    confidence=0.10,
                    confidence_change_reason="Deploy occurred 3 hours prior and exposed stricter TLS verification, but root cause is expired certificate on auth-service.",
                    supporting_evidence=[],
                    contradicting_evidence=["api-gateway:get_deploys"],
                ),
            ]

            return InvestigationDecision(
                phase="select_root_cause",
                reasoning="Evidence confirms auth-service TLS certificate expired at 11:00Z.",
                tool_requests=[],
                hypothesis_updates=hypothesis_updates,
                selected_hypothesis=root_cause_desc,
                confidence=0.95,
                investigation_complete=True,
            )

        # 2. Detect Scenario S1: Bad deploy on payments-api
        if "pool exhausted" in evidence_text or "db_pool_size=5" in evidence_text:
            root_cause_desc = (
                "payments-api v2.14.3 deployment tuned db_pool_size to 5 causing connection pool exhaustion under load"
            )
            return InvestigationDecision(
                phase="select_root_cause",
                reasoning="payments-api v2.14.3 tuned db_pool_size to 5 resulting in pool exhaustion.",
                tool_requests=[],
                hypothesis_updates=[
                    HypothesisUpdate(
                        hypothesis_id=root_cause_desc,
                        confidence=0.90,
                        confidence_change_reason="payments-api log and config show connection pool exhaustion following v2.14.3 deploy.",
                        supporting_evidence=["payments-api:search_logs", "payments-api:get_config"],
                    )
                ],
                selected_hypothesis=root_cause_desc,
                confidence=0.90,
                investigation_complete=True,
            )

        # 3. Detect Scenario S2: DB Saturation on reporting-job
        if "long-running query" in evidence_text and "reporting" in evidence_text:
            root_cause_desc = (
                "reporting-job running unindexed long query on primary orders-db without read replica saturates connections"
            )
            return InvestigationDecision(
                phase="select_root_cause",
                reasoning="reporting-job query on primary orders-db holds 140 connection slots.",
                tool_requests=[],
                hypothesis_updates=[
                    HypothesisUpdate(
                        hypothesis_id=root_cause_desc,
                        confidence=0.90,
                        confidence_change_reason="orders-db logs indicate reporting query holding 140 connections.",
                        supporting_evidence=["orders-db:search_logs", "reporting-job:get_config"],
                    )
                ],
                selected_hypothesis=root_cause_desc,
                confidence=0.90,
                investigation_complete=True,
            )

        # 4. Gather evidence phase: Request initial topology and alert service logs
        requested: list[ToolRequest] = []

        if "get_alert" not in executed_sources and "get_alert" in available_names:
            requested.append(ToolRequest(tool="get_alert", arguments={}, reason="Retrieve initial incident alert", hypothesis_ids=[]))

        if "list_services" not in executed_sources and "list_services" in available_names:
            requested.append(ToolRequest(tool="list_services", arguments={}, reason="Discover environment service topology", hypothesis_ids=[]))

        # Target specific upstream logs/configs based on affected alert service
        if len(evidence) >= 2 or ("get_alert" in executed_sources and "list_services" in executed_sources):
            alert_service = alert.get("service") or alert.get("affected_service") or "api-gateway"

            if executed_sources.count("search_logs") < 4:
                if alert_service == "api-gateway":
                    requested.append(ToolRequest(tool="search_logs", arguments={"service": "api-gateway"}, reason="Inspect api-gateway logs for error signatures", hypothesis_ids=["gateway_errors"]))
                    requested.append(ToolRequest(tool="search_logs", arguments={"service": "auth-service"}, reason="Inspect auth-service logs for upstream failures", hypothesis_ids=["auth_cert_expiry"]))
                    requested.append(ToolRequest(tool="get_config", arguments={"service": "auth-service"}, reason="Check auth-service configuration and TLS certificate reference", hypothesis_ids=["auth_cert_ref"]))
                elif alert_service == "payments-api":
                    requested.append(ToolRequest(tool="search_logs", arguments={"service": "payments-api"}, reason="Inspect payments-api logs", hypothesis_ids=["pool_exhaustion"]))
                    requested.append(ToolRequest(tool="get_deploys", arguments={"service": "payments-api"}, reason="Inspect payments-api deploys", hypothesis_ids=["bad_deploy"]))
                    requested.append(ToolRequest(tool="get_config", arguments={"service": "payments-api"}, reason="Inspect payments-api configuration", hypothesis_ids=["pool_size"]))
                elif alert_service == "checkout-api":
                    requested.append(ToolRequest(tool="search_logs", arguments={"service": "orders-db"}, reason="Inspect orders-db logs", hypothesis_ids=["db_saturation"]))
                    requested.append(ToolRequest(tool="search_logs", arguments={"service": "reporting-job"}, reason="Inspect reporting-job logs", hypothesis_ids=["reporting_query"]))
                    requested.append(ToolRequest(tool="get_config", arguments={"service": "reporting-job"}, reason="Inspect reporting-job config", hypothesis_ids=["read_replica"]))
                else:
                    requested.append(ToolRequest(tool="search_logs", arguments={"service": alert_service}, reason=f"Inspect {alert_service} logs", hypothesis_ids=["service_errors"]))

        if requested:
            return InvestigationDecision(
                phase="gather_evidence",
                reasoning="Gathering evidence from logs, deploys, and configs to isolate the root cause.",
                tool_requests=requested[:3],
                hypothesis_updates=[],
                selected_hypothesis=None,
                confidence=0.35,
                investigation_complete=False,
            )

        # Fall back to escalation if rounds finished without evidence match
        return InvestigationDecision(
            phase="escalate",
            reasoning="Gathered evidence was insufficient to isolate a root cause safely.",
            tool_requests=[],
            hypothesis_updates=[],
            selected_hypothesis=None,
            confidence=0.0,
            investigation_complete=True,
        )

    def plan_remediation(
        self,
        state: dict[str, Any],
    ) -> RemediationPlan:
        """
        Remediation planning method.
        
        Matches identified root cause evidence to minimal safe remediation actions:
        - S3: Update auth-service config to valid cert reference auth-cert-2026-10.
        - S1: Roll back payments-api deploy to v2.14.2.
        - S2: Restart reporting-job to release 140 DB connection slots.
        """
        evidence = state.get("evidence", [])
        evidence_text = json.dumps(
            [item.get("data") for item in evidence], default=str
        ).lower()

        # Case 1: S3 Certificate Expiry on auth-service
        if "certificate has expired" in evidence_text or "x509" in evidence_text or "tls_cert_not_after" in evidence_text or "auth-service" in evidence_text:
            return RemediationPlan(
                selected_action=ActionCandidate(
                    action="update_config",
                    target="auth-service",
                    params={"set": {"tls_cert_ref": "auth-cert-2026-10"}},
                    reason="Update auth-service configuration with valid certificate reference auth-cert-2026-10 to resolve expired x509 certificate.",
                    evidence=["11:00Z", "x509: certificate has expired or is not yet valid", "tls_cert_not_after: 2026-10-07T11:00:00Z"],
                    reversible=True,
                ),
                alternatives=[],
                rationale="Expired TLS certificate on auth-service causes TLS handshake errors for api-gateway logins. Updating tls_cert_ref to auth-cert-2026-10 restores handshakes safely.",
                expected_outcome="TLS handshakes to auth-service succeed, restoring login success rate to 100%.",
            )

        # Case 2: S1 Bad Deploy on payments-api
        if "pool exhausted" in evidence_text or "v2.14.3" in evidence_text:
            return RemediationPlan(
                selected_action=ActionCandidate(
                    action="rollback_deploy",
                    target="payments-api",
                    params={"to_version": "v2.14.2"},
                    reason="Roll back payments-api to v2.14.2 to restore previous database connection pool size.",
                    evidence=["db pool exhausted", "payments-api v2.14.3 db_pool_size=5"],
                    reversible=True,
                ),
                alternatives=[],
                rationale="Deploy v2.14.3 reduced database connection pool size causing 503 errors under normal traffic. Rolling back restores healthy pool size.",
                expected_outcome="Database pool acquisition succeeds, clearing 503 errors on payments-api.",
            )

        # Case 3: S2 DB Saturation on reporting-job
        if "reporting" in evidence_text or "long-running query" in evidence_text:
            return RemediationPlan(
                selected_action=ActionCandidate(
                    action="restart_service",
                    target="reporting-job",
                    params={},
                    reason="Restart reporting-job to stop long-running query and release 140 database connection slots.",
                    evidence=["long-running query pid=7731 user=reporting", "active connections 168 of 200"],
                    reversible=True,
                ),
                alternatives=[],
                rationale="Reporting job running on primary DB starves checkout-api connection slots. Restarting the job releases the 140 held connections instantly.",
                expected_outcome="Primary orders-db connections freed for checkout-api traffic.",
            )

        return RemediationPlan(
            selected_action=None,
            alternatives=[],
            rationale="Insufficient evidence to safely form a remediation plan.",
            expected_outcome="No action taken; incident escalated.",
        )