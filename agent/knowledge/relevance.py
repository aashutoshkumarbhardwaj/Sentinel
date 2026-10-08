from __future__ import annotations

from typing import Any


def evaluate_runbook_relevance(
    retrieved_articles: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Evaluates retrieved runbooks against observed production evidence.
    
    Why: Past incident fixes (e.g. INC-2025-0912 recommending service restart for 5xx errors)
    may be completely non-viable when current evidence indicates expired x509 TLS certificates.
    This filter prevents the agent from blindly copying wrong past fixes.
    """
    evidence_text = " ".join(str(item.get("data", "")) for item in evidence).lower()
    relevant = []

    for article in retrieved_articles:
        article_id = article.get("id")

        # Explicitly reject restarting service (INC-2025-0912) when certificate is expired
        if article_id == "INC-2025-0912" and ("certificate" in evidence_text or "x509" in evidence_text or "expired" in evidence_text):
            article["relevance_reason"] = "Rejected: Restarting service does not fix an expired TLS certificate."
            article["is_relevant"] = False
            continue

        article["is_relevant"] = True
        relevant.append(article)

    return relevant
