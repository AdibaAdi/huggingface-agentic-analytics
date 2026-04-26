"""Configuration utilities for the Hugging Face Agentic Analytics app."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

# Load environment variables from .env for local development.
load_dotenv()


@dataclass
class AppConfig:
    """Runtime config loaded from environment variables."""

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/hf_analytics"
    )
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    hf_token: str = os.getenv("HF_TOKEN", "")
    e2b_api_key: str = os.getenv("E2B_API_KEY", "")
    hf_tags: List[str] = field(
        default_factory=lambda: [
            "text-generation",
            "image-text-to-text",
            "text-classification",
            "summarization",
            "automatic-speech-recognition",
        ]
    )
    top_n_per_tag: int = int(os.getenv("TOP_N_PER_TAG", "5"))

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_hf_token(self) -> bool:
        return bool(self.hf_token)


def get_config() -> AppConfig:
    """Factory helper so modules can import lazily."""

    return AppConfig()
