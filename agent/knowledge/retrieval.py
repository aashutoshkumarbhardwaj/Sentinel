from __future__ import annotations

from typing import Any


class KnowledgeArticle:
    """Represents a past incident record or SRE runbook entry in the knowledge base."""

    def __init__(
        self,
        article_id: str,
        title: str,
        category: str,
        content: str,
        recommended_action: str | None = None,
    ):
        self.article_id = article_id
        self.title = title
        self.category = category
        self.content = content
        self.recommended_action = recommended_action


# Simulated knowledge base of past incidents and operational runbooks
KNOWLEDGE_BASE: list[KnowledgeArticle] = [
    KnowledgeArticle(
        article_id="INC-2025-0912",
        title="Transient 5xx errors on API Gateway",
        category="past_incident",
        content="Transient 5xx error spikes caused by memory pressure resolved by restarting api-gateway.",
        recommended_action="restart_service:api-gateway",
    ),
    KnowledgeArticle(
        article_id="RUNBOOK-DB-POOL",
        title="Database Connection Pool Exhaustion",
        category="runbook",
        content="When services report pool exhaustion after a deploy, verify pool_size config or rollback deploy.",
        recommended_action="rollback_deploy",
    ),
    KnowledgeArticle(
        article_id="RUNBOOK-READ-REPLICA",
        title="Database High Connection Utilization",
        category="runbook",
        content="Heavy reporting queries taking connections should be shifted to read replicas.",
        recommended_action="update_config",
    ),
]


class KnowledgeRetriever:
    """
    Knowledge retrieval engine for searching past incident history and runbooks.
    
    Why: Grounding agent reasoning in institutional knowledge prevents reinventing known solutions.
    """

    def search(self, query: str, service: str | None = None) -> list[dict[str, Any]]:
        """Search runbooks matching service name and query terms."""
        query_lower = query.lower()
        results = []

        for article in KNOWLEDGE_BASE:
            score = 0
            if service and service.lower() in article.content.lower():
                score += 2
            for word in query_lower.split():
                if len(word) > 3 and word in article.content.lower():
                    score += 1

            if score > 0:
                results.append({
                    "id": article.article_id,
                    "title": article.title,
                    "score": score,
                    "content": article.content,
                    "recommended_action": article.recommended_action,
                })

        results.sort(key=lambda item: item["score"], reverse=True)
        return results
