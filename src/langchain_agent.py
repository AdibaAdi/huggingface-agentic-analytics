"""LangChain-based natural language router for deterministic actions."""

from __future__ import annotations

import json
from dataclasses import dataclass

from config import get_config

SUPPORTED_ACTIONS = {
    "highest_discussions",
    "table_discussions_weekday",
    "day_most_created",
    "day_most_closed",
    "chart_total_discussions_over_time",
    "chart_discussions_distribution_by_model",
    "chart_likes_per_model",
    "chart_downloads_per_model",
    "chart_closed_discussions_per_week",
    "chart_open_closed_per_model",
    "forecast_created_discussions",
    "forecast_closed_discussions",
    "forecast_pull_requests",
    "forecast_commits",
}


@dataclass
class RouteResult:
    action: str
    reason: str


def route_question(question: str) -> RouteResult:
    """Use LLM routing to classify the user's natural language request into a supported action."""

    cfg = get_config()
    if not cfg.has_openai:
        return RouteResult(
            action="error",
            reason=(
                "OPENAI_API_KEY is missing. Set OPENAI_API_KEY to enable natural language routing "
                "with the LLM."
            ),
        )

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", api_key=cfg.openai_api_key, temperature=0)
        system_prompt = (
            "You are a strict router for an analytics app. "
            "Classify the user question into exactly one supported action. "
            "Supported actions: "
            + ", ".join(sorted(SUPPORTED_ACTIONS))
            + ". "
            "Return ONLY strict JSON with exactly two keys: action and reason. "
            "The action value must be one of the supported actions."
        )

        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User question: {question}"),
            ]
        )
        text = response.content if isinstance(response.content, str) else str(response.content)
        data = json.loads(text)
        action = data.get("action")
        reason = data.get("reason", "LLM route")

        if action not in SUPPORTED_ACTIONS:
            return RouteResult(
                action="error",
                reason=(
                    f"LLM returned unsupported action '{action}'. "
                    "Please rephrase your request as a natural language analytics question."
                ),
            )

        return RouteResult(action=action, reason=reason)
    except Exception as exc:
        return RouteResult(
            action="error",
            reason=(
                "LLM routing failed. Please try again with a clear natural language prompt. "
                f"Technical detail: {exc}"
            ),
        )
