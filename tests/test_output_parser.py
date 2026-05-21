"""Tests for src/app/output_parser.py."""

from __future__ import annotations

import json

from app.output_parser import parse_stdout


def test_parse_stdout_extracts_table():
    stdout = (
        "Top repo is ok/repo with 5 discussions.\n"
        "<<<TABLE_START>>>\n"
        "model_id,discussion_count\n"
        "ok/repo,5\n"
        "other/repo,2\n"
        "<<<TABLE_END>>>\n"
    )
    parsed = parse_stdout(stdout)
    assert len(parsed.tables) == 1
    assert list(parsed.tables[0].columns) == ["model_id", "discussion_count"]
    assert parsed.tables[0].iloc[0]["model_id"] == "ok/repo"
    assert "Top repo is" in parsed.text_answer
    assert "<<<TABLE_START>>>" not in parsed.text_answer


def test_parse_stdout_extracts_chart():
    fig_json = {
        "data": [{"type": "bar", "x": ["a"], "y": [1]}],
        "layout": {"title": {"text": "demo"}},
    }
    stdout = (
        "Here is the chart.\n"
        "<<<CHART_START>>>\n"
        f"{json.dumps(fig_json)}\n"
        "<<<CHART_END>>>\n"
    )
    parsed = parse_stdout(stdout)
    assert len(parsed.charts) == 1
    assert parsed.charts[0]["data"][0]["type"] == "bar"
    assert "<<<CHART_START>>>" not in parsed.text_answer


def test_parse_stdout_handles_no_data_marker():
    parsed = parse_stdout("NO_DATA")
    assert parsed.no_data is True
    assert parsed.tables == []
    assert parsed.charts == []


def test_parse_stdout_empty_stdout_returns_empty_result():
    parsed = parse_stdout("")
    assert parsed.tables == []
    assert parsed.charts == []
    assert parsed.text_answer == ""
    assert parsed.no_data is False


def test_parse_stdout_handles_mixed_table_and_chart():
    fig_json = {"data": [], "layout": {}}
    stdout = (
        "Mixed output.\n"
        "<<<TABLE_START>>>\n"
        "a,b\n1,2\n"
        "<<<TABLE_END>>>\n"
        "<<<CHART_START>>>\n"
        f"{json.dumps(fig_json)}\n"
        "<<<CHART_END>>>\n"
    )
    parsed = parse_stdout(stdout)
    assert len(parsed.tables) == 1
    assert len(parsed.charts) == 1
    assert "Mixed output." in parsed.text_answer
