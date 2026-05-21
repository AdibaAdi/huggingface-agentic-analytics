"""Tests for src/etl/transform_clean.py."""

from __future__ import annotations

from datetime import datetime

import pytest

from etl.transform_clean import (
    add_weekday_column,
    clean_discussion_rows,
    clean_model_rows,
)


def test_clean_model_rows_drops_rows_missing_required_fields():
    rows = [
        {"model_id": "ok/repo", "tag": "text-generation", "likes": 5, "downloads": 10},
        {"model_id": None, "tag": "text-generation"},
        {"model_id": "missing/tag", "tag": None},
    ]
    cleaned = clean_model_rows(rows)
    assert len(cleaned) == 1
    assert cleaned[0]["model_id"] == "ok/repo"


def test_clean_model_rows_coerces_negative_counts_to_zero():
    rows = [
        {
            "model_id": "weird/repo",
            "tag": "text-generation",
            "likes": -3,
            "downloads": -10,
        }
    ]
    cleaned = clean_model_rows(rows)
    assert cleaned[0]["likes"] == 0
    assert cleaned[0]["downloads"] == 0


def test_clean_discussion_rows_normalizes_status():
    rows = [
        {
            "model_id": "ok/repo",
            "hf_discussion_num": 1,
            "title": "Q",
            "status": "CLOSED",
            "created_at": datetime(2025, 1, 6),  # a Monday
        },
        {
            "model_id": "ok/repo",
            "hf_discussion_num": 2,
            "title": "Q2",
            "status": "garbage",
            "created_at": datetime(2025, 1, 7),  # a Tuesday
        },
    ]
    cleaned = clean_discussion_rows(rows)
    assert cleaned[0]["status"] == "closed"
    assert cleaned[1]["status"] == "open"


def test_clean_discussion_rows_adds_weekday():
    rows = [
        {
            "model_id": "ok/repo",
            "hf_discussion_num": 1,
            "title": "Q",
            "status": "open",
            "created_at": datetime(2025, 1, 6),  # Monday
        }
    ]
    cleaned = clean_discussion_rows(rows)
    assert cleaned[0]["weekday"] == "Monday"


def test_clean_discussion_rows_drops_rows_missing_required():
    rows = [
        {"model_id": None, "hf_discussion_num": 1},
        {"model_id": "ok/repo", "hf_discussion_num": None},
        {
            "model_id": "ok/repo",
            "hf_discussion_num": 5,
            "title": "Q",
            "status": "open",
            "created_at": None,
        },
    ]
    cleaned = clean_discussion_rows(rows)
    assert len(cleaned) == 1
    assert cleaned[0]["weekday"] is None  # no created_at -> no weekday


def test_add_weekday_column_handles_none():
    rows = [{"created_at": None}, {"created_at": datetime(2025, 1, 8)}]  # Wed
    out = add_weekday_column(rows)
    assert out[0]["weekday"] is None
    assert out[1]["weekday"] == "Wednesday"


@pytest.mark.parametrize(
    "raw_status,expected",
    [
        ("open", "open"),
        ("OPEN", "open"),
        ("closed", "closed"),
        ("Closed", "closed"),
        ("  closed  ", "closed"),
        ("nonsense", "open"),
        (None, "open"),
    ],
)
def test_status_canonicalization(raw_status, expected):
    rows = [
        {
            "model_id": "ok/repo",
            "hf_discussion_num": 1,
            "title": "Q",
            "status": raw_status,
            "created_at": datetime(2025, 1, 6),
        }
    ]
    cleaned = clean_discussion_rows(rows)
    assert cleaned[0]["status"] == expected
