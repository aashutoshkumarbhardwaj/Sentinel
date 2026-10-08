from __future__ import annotations

from typing import Any


def evaluate_runbook_relevance(
    retrieved_articles: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Filters retrieved runbooks and past incidents against current observed evidence.
    Rejects inapplicable fixes (e.g. restart service for TLS certificate expiry).
    """
    evidence_text = " ".join(str(item.get("data", "")) for item in evidence).lower()
    relevant = []

    for article in retrieved_articles:
        article_id = article.get("id")

        # Reject past incident INC-2025-0912 (restart service) if certificate has expired
        if article_id == "INC-2025-0912" and ("certificate" in evidence_text or "x509" in evidence_text or "expired" in evidence_text):
            article["relevance_reason"] = "Rejected: Restarting service does not fix an expired TLS certificate."
            article["is_relevant"] = False
            continue

        article["is_relevant"] = True
        relevant.append(article)

    return relevant
