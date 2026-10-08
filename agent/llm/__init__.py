from agent.llm.fallback import DeterministicDecisionEngine
from agent.llm.model import build_llm_engine


def get_decision_engine():
    llm_engine = build_llm_engine()

    if llm_engine is not None:
        return llm_engine

    return DeterministicDecisionEngine()