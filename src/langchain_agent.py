"""LangChain-based natural language router for deterministic actions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from config import get_config


@dataclass
class RouteResult:
    action: str
    reason: str


def _keyword_route(question: str) -> RouteResult:
    q = question.lower()
    if "highest" in q and "discussion" in q and ("repo" in q or "model" in q):
        return RouteResult("highest_discussions", "Keyword match for highest discussions query.")
    if "every day" in q or ("monday" in q and "sunday" in q):
        return RouteResult("table_discussions_weekday", "Keyword match for weekday table query.")
    if "highest" in q and "closed" in q and "day" in q:
        return RouteResult("day_most_closed", "Keyword match for highest closed day query.")
    if "highest" in q and "day" in q and "discussion" in q:
        return RouteResult("day_most_created", "Keyword match for highest created day query.")
    return RouteResult("highest_discussions", "Fallback route.")


def route_question(question: str) -> RouteResult:
    """Try GPT routing first; fallback to deterministic keyword routing."""

    cfg = get_config()
    if not cfg.has_openai:
        return _keyword_route(question)

    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model=cfg.openai_model, api_key=cfg.openai_api_key, temperature=0)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Route the user question to one of: "
                    "highest_discussions, table_discussions_weekday, day_most_created, day_most_closed. "
                    "Return strict JSON object with keys action and reason.",
                ),
                ("human", "Question: {question}"),
            ]
        )
        response = llm.invoke(prompt.format_messages(question=question))
        text = response.content if isinstance(response.content, str) else str(response.content)
        data = json.loads(re.search(r"\{.*\}", text, flags=re.S).group(0))
        action = data.get("action", "")
        if action in {
            "highest_discussions",
            "table_discussions_weekday",
            "day_most_created",
            "day_most_closed",
        }:
            return RouteResult(action=action, reason=data.get("reason", "LLM route"))
    except Exception:
        pass

    return _keyword_route(question)
