"""End to end pipeline orchestrator.

Wires the extract, transform, and load stages together and returns a
structured summary. The Streamlit app and the assignment grader both
invoke this entry point to populate the database from scratch.

Run from the repository root:

    python -m src.etl.run_pipeline
"""

from __future__ import annotations

import json
from typing import Any

from config import get_config
from etl.extract_discussions import extract_discussions_for_repo
from etl.extract_hf_models import extract_top_models
from etl.load_postgres import load_discussions, load_models
from etl.transform_clean import clean_discussion_rows, clean_model_rows
from utils.logging_utils import get_logger

_log = get_logger("etl.pipeline")


def run() -> dict[str, Any]:
    """Run the full extract, transform, load pipeline.

    Returns a dictionary summarizing how many rows were touched at each step
    plus a list of repos whose discussions could not be fetched.
    """
    cfg = get_config()

    raw_models = extract_top_models(cfg)
    clean_models = clean_model_rows(raw_models)
    models_loaded = load_models(clean_models)

    all_discussion_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for m in clean_models:
        rows, err = extract_discussions_for_repo(cfg, m["model_id"])
        if err is not None:
            errors.append(err)
        all_discussion_rows.extend(rows)

    clean_discussions = clean_discussion_rows(all_discussion_rows)
    discussions_loaded = load_discussions(clean_discussions)

    summary = {
        "models_seen": len(raw_models),
        "models_cleaned": len(clean_models),
        "models_loaded": models_loaded,
        "discussions_seen": len(all_discussion_rows),
        "discussions_cleaned": len(clean_discussions),
        "discussions_loaded": discussions_loaded,
        "fetch_errors": errors,
        "limitations": [
            "Hugging Face downloads counts are a proxy for usage, not production load.",
            "Closed discussions are not always resolved discussions.",
            "Some repos have discussions disabled and are skipped (logged in fetch_errors).",
            "Repository creation dates can be missing for older or migrated repos.",
        ],
    }
    _log.info(
        "Pipeline finished. Models loaded=%d, Discussions loaded=%d, Errors=%d",
        summary["models_loaded"],
        summary["discussions_loaded"],
        len(summary["fetch_errors"]),
    )
    return summary


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
