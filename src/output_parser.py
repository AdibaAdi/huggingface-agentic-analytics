"""Parses the marker-delimited output produced by generated scripts.

The LLM-generated code prints results between markers:
    <<<TABLE_START>>> ... <<<TABLE_END>>>     -> CSV table
    <<<CHART_START>>> ... <<<CHART_END>>>     -> Plotly figure JSON
    'NO_DATA'                                  -> empty result
Anything outside markers is treated as the textual answer.
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

TABLE_RE = re.compile(r"<<<TABLE_START>>>(.*?)<<<TABLE_END>>>", re.DOTALL)
CHART_RE = re.compile(r"<<<CHART_START>>>(.*?)<<<CHART_END>>>", re.DOTALL)


@dataclass
class ParsedOutput:
    text_answer: str = ""
    tables: list[pd.DataFrame] = field(default_factory=list)
    charts: list[dict[str, Any]] = field(default_factory=list)
    raw_stdout: str = ""
    no_data: bool = False


def parse_stdout(stdout: str) -> ParsedOutput:
    out = ParsedOutput(raw_stdout=stdout)
    if not stdout:
        return out

    if "NO_DATA" in stdout:
        out.no_data = True

    # Extract chart JSON blocks
    for match in CHART_RE.findall(stdout):
        try:
            out.charts.append(json.loads(match.strip()))
        except json.JSONDecodeError:
            pass

    # Extract CSV tables
    for match in TABLE_RE.findall(stdout):
        csv_text = match.strip()
        if csv_text:
            try:
                df = pd.read_csv(io.StringIO(csv_text))
                out.tables.append(df)
            except Exception:
                pass

    # Strip the marker blocks out of the text answer
    cleaned = TABLE_RE.sub("", stdout)
    cleaned = CHART_RE.sub("", cleaned)
    out.text_answer = cleaned.strip()
    return out
