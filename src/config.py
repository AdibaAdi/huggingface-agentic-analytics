"""Runtime configuration loaded from environment variables.

This module reads ``.env`` from the repository root and exposes a typed
``AppConfig`` dataclass to the rest of the application. Centralizing
configuration in one place keeps secrets out of source code and makes
it obvious which environment variables a given run depends on.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Load .env from the repository root (parent of src/) and also from the
# current working directory as a fallback when running from elsewhere.
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
load_dotenv()


@dataclass
class AppConfig:
    """Typed runtime config. All fields are populated from environment variables."""

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/hf_analytics",
    )
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    hf_token: str = os.getenv("HUGGINGFACE_API_TOKEN", "")
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

    @property
    def has_e2b(self) -> bool:
        return bool(self.e2b_api_key)


def get_config() -> AppConfig:
    """Factory helper so modules can import config lazily."""
    return AppConfig()


# Make sure OPENAI_API_KEY is exported for downstream libraries (LlamaIndex, OpenAI SDK)
# even when the caller only set it inside .env.
_cfg = AppConfig()
if _cfg.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = _cfg.openai_api_key
