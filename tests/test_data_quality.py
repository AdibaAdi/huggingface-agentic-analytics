"""Tests for src/analysis/data_quality.py.

These tests target the pure ``validate_discussions`` helper, which does not
require a live database connection.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from analysis.data_quality import validate_discussions


def _sample_df():
    return pd.DataFrame(
        [
            {
                "model_id": "ok/repo",
                "hf_discussion_num": 1,
                "status": "open",
                "created_at": datetime(2025, 1, 6),
            },
            {
                "model_id": "ok/repo",
                "hf_discussion_num": 1,  # duplicate by (model_id, num)
                "status": "open",
                "created_at": datetime(2025, 1, 6),
            },
            {
                "model_id": "ok/repo",
                "hf_discussion_num": 2,
                "status": "garbage",
                "created_at": None,
            },
            {
                "model_id": None,
                "hf_discussion_num": 3,
                "status": "closed",
                "created_at": datetime(2025, 1, 7),
            },
        ]
    )


def test_validate_discussions_detects_duplicates():
    df = _sample_df()
    result = validate_discussions(df)
    assert result["duplicate_discussions"] == 1


def test_validate_discussions_detects_missing_model_id():
    df = _sample_df()
    result = validate_discussions(df)
    assert result["missing_model_id"] == 1


def test_validate_discussions_detects_missing_created_at():
    df = _sample_df()
    result = validate_discussions(df)
    assert result["missing_created_at"] == 1


def test_validate_discussions_detects_invalid_status():
    df = _sample_df()
    result = validate_discussions(df)
    assert result["invalid_status_values"] == 1


def test_validate_discussions_empty_df_returns_zeros():
    result = validate_discussions(pd.DataFrame())
    assert result == {
        "missing_model_id": 0,
        "missing_created_at": 0,
        "duplicate_discussions": 0,
        "invalid_status_values": 0,
    }


def test_validate_discussions_clean_df_returns_zeros():
    df = pd.DataFrame(
        [
            {
                "model_id": "a/b",
                "hf_discussion_num": 1,
                "status": "open",
                "created_at": datetime(2025, 1, 6),
            },
            {
                "model_id": "a/b",
                "hf_discussion_num": 2,
                "status": "closed",
                "created_at": datetime(2025, 1, 7),
            },
        ]
    )
    result = validate_discussions(df)
    assert result == {
        "missing_model_id": 0,
        "missing_created_at": 0,
        "duplicate_discussions": 0,
        "invalid_status_values": 0,
    }
