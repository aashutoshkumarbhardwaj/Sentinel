from __future__ import annotations

import os
from typing import Any, Protocol

from agent.llm.schemas import (
    InvestigationDecision,
    RemediationPlan,
)


class DecisionEngine(Protocol):
    """Protocol interface for decision engines (both LLM-backed and offline deterministic)."""
    def investigate(
        self,
        state: dict[str, Any],
        available_tools: list[dict[str, Any]],
    ) -> InvestigationDecision:
        ...

    def plan_remediation(
        self,
        state: dict[str, Any],
    ) -> RemediationPlan:
        ...


class StructuredLLMEngine:
    """
    LLM-backed decision engine using LangChain structured output.

    Why: Enforces that the model produces validated Pydantic objects instead of free-form text.
    """

    def __init__(self, model: Any):
        self.model = model

        # Bind Pydantic schemas for structured output enforcement
        self.investigation_model = model.with_structured_output(
            InvestigationDecision
        )

        self.remediation_model = model.with_structured_output(
            RemediationPlan
        )

    def investigate(
        self,
        state: dict[str, Any],
        available_tools: list[dict[str, Any]],
    ) -> InvestigationDecision:
        """Construct investigation prompt and query structured LLM."""
        from agent.llm.prompts import build_investigation_prompt

        prompt = build_investigation_prompt(
            state=state,
            available_tools=available_tools,
        )

        return self.investigation_model.invoke(prompt)

    def plan_remediation(
        self,
        state: dict[str, Any],
    ) -> RemediationPlan:
        """Construct remediation prompt and query structured LLM."""
        from agent.llm.prompts import build_remediation_prompt

        prompt = build_remediation_prompt(state)

        return self.remediation_model.invoke(prompt)


def build_llm_engine() -> StructuredLLMEngine | None:
    """
    Creates the LLM engine when OPENAI_API_KEY environment variable is configured.

    Why: Returning None when no API key is present allows offline evaluation mode.
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    model_name = os.getenv("OPENAI_MODEL")

    if not model_name:
        raise RuntimeError(
            "OPENAI_MODEL must be configured when OPENAI_API_KEY is set"
        )

    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=model_name,
        temperature=0,
    )

    return StructuredLLMEngine(model)