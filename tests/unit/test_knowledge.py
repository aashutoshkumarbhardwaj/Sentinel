from agent.knowledge.retrieval import KnowledgeRetriever
from agent.knowledge.relevance import evaluate_runbook_relevance


def test_knowledge_retrieval_and_relevance():
    retriever = KnowledgeRetriever()
    results = retriever.search(query="5xx error api gateway", service="api-gateway")
    assert len(results) > 0

    # Test filtering out restart runbook when evidence indicates expired cert
    evidence = [{"data": "x509: certificate has expired on auth-service"}]
    relevant = evaluate_runbook_relevance(results, evidence)

    # INC-2025-0912 should be rejected because restart does not fix expired cert
    rejected_ids = [item["id"] for item in results if item["id"] not in [r["id"] for r in relevant]]
    assert "INC-2025-0912" in rejected_ids
