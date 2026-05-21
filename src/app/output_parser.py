"""Parses the marker delimited stdout produced by generated scripts.

The LLM is instructed to surround any table or chart payload with markers:

    <<<TABLE_START>>> ... CSV ... <<<TABLE_END>>>
    <<<CHART_START>>> ... Plotly figure JSON ... <<<CHART_END>>>
    NO_DATA                                       -> empty result

Anything outside of the markers is treated as the textual answer.
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
    """Return a :class:`ParsedOutput` extracted from ``stdout``."""
    out = ParsedOutput(raw_stdout=stdout)
    if not stdout:
        return out

    if "NO_DATA" in stdout:
        out.no_data = True

    for match in CHART_RE.findall(stdout):
        try:
            out.charts.append(json.loads(match.strip()))
        except json.JSONDecodeError:
            pass

    for match in TABLE_RE.findall(stdout):
        csv_text = match.strip()
        if not csv_text:
            continue
        try:
            df = pd.read_csv(io.StringIO(csv_text))
            out.tables.append(df)
        except Exception:
            pass

    cleaned = TABLE_RE.sub("", stdout)
    cleaned = CHART_RE.sub("", cleaned)
    out.text_answer = cleaned.strip()
    return out
