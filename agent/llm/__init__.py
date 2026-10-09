import os
from agent.llm.fallback import DeterministicDecisionEngine
from agent.llm.model import build_llm_engine


def get_decision_engine():
    """
    Returns decision engine instance.
    
    Why: Prefers live LLM decision engine when credentials are provided,
    while falling back to DeterministicDecisionEngine in offline mode or during pytest suite.
    """
    if os.getenv("OFFLINE_MODE") == "1" or os.getenv("PYTEST_CURRENT_TEST"):
        return DeterministicDecisionEngine()

    llm_engine = build_llm_engine()

    if llm_engine is not None:
        return llm_engine

    return DeterministicDecisionEngine()