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
    Uses method="function_calling" for broad compatibility across OpenAI and OpenRouter model providers.
    """

    def __init__(self, model: Any):
        self.model = model

        # Bind Pydantic schemas using function_calling method for multi-provider compatibility
        self.investigation_model = model.with_structured_output(
            InvestigationDecision,
            method="function_calling",
        )

        self.remediation_model = model.with_structured_output(
            RemediationPlan,
            method="function_calling",
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
    Creates an OpenAI or OpenRouter LLM engine when credentials are configured.

    Why: Automatically loads .env credentials and configures OpenRouter base_url
    and method="function_calling" when OpenRouter keys (`sk-or-v1...`) or OPENROUTER_API_KEY are used.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    # Detect OpenRouter key or configuration
    is_openrouter = api_key.startswith("sk-or-v1") or bool(os.getenv("OPENROUTER_API_KEY"))

    default_model = "meta-llama/llama-3.3-70b-instruct" if is_openrouter else "gpt-4o-mini"
    model_name = os.getenv("OPENROUTER_MODEL") or os.getenv("OPENAI_MODEL") or default_model

    # Use meta-llama/llama-3.3-70b-instruct for free tier if nemotron reasoning model was configured
    if is_openrouter and "nemotron" in model_name.lower():
        model_name = "meta-llama/llama-3.3-70b-instruct"

    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": model_name,
        "api_key": api_key,
        "temperature": 0,
    }

    if is_openrouter:
        kwargs["base_url"] = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    model = ChatOpenAI(**kwargs)
    return StructuredLLMEngine(model)