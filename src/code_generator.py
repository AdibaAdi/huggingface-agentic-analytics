"""LlamaIndex agent that converts a natural language question into Python code.

The LLM is given the Postgres schema + a strict prompt. It must produce a
self-contained Python script that:
  - reads from Postgres via SQLAlchemy
  - uses Polars / Pandas / Plotly / Prophet / Statsmodels as needed
  - prints a textual answer AND/OR writes a Plotly figure JSON to stdout

The generated script is then executed inside ONE of four sandboxes
(Bonus 2 alternatives) -- this module is the "code generation" half only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI

from config import get_config

SCHEMA_DESCRIPTION = """
You will write Python that queries a Postgres database with this exact schema:

Table: model_repos
  id            INTEGER PRIMARY KEY
  model_id      VARCHAR        -- e.g. 'meta-llama/Llama-3.1-8B-Instruct'
  tag           VARCHAR        -- HF category, e.g. 'text-generation'
  author        VARCHAR
  likes         INTEGER        -- proxy for "stars"
  downloads     INTEGER        -- proxy for "forks/usage"
  pipeline_tag  VARCHAR
  created_at    TIMESTAMP

Table: discussions
  id                  INTEGER PRIMARY KEY
  repo_id             INTEGER  -- FK -> model_repos.id
  hf_discussion_num   INTEGER
  title               TEXT
  author              VARCHAR
  is_pull_request     BOOLEAN  -- proxy for pull requests
  status              VARCHAR  -- 'open' or 'closed'
  created_at          TIMESTAMP
  closed_at           TIMESTAMP

Connection: SQLAlchemy engine is available via:
    from sqlalchemy import create_engine, text
    engine = create_engine(DATABASE_URL)   # DATABASE_URL is provided as a Python variable
"""

CODE_GEN_SYSTEM_PROMPT = f"""You are a senior Python data engineer. Given a user's
natural-language analytics question about Hugging Face model repos, you must
generate a SINGLE self-contained Python 3.11 script that answers it.

{SCHEMA_DESCRIPTION}

STRICT RULES:
1. Output ONLY Python code. No markdown fences, no commentary, no explanations.
2. The variable DATABASE_URL is already defined in the execution scope -- USE IT.
   Do not redefine it. Do not hardcode credentials.
3. For TEXT/TABLE answers:
     - print() a one-line human readable answer first
     - then print the resulting table as CSV. EACH MARKER MUST BE ON ITS OWN LINE:
           print('<<<TABLE_START>>>')
           print(df.to_csv(index=False))
           print('<<<TABLE_END>>>')
4. For CHART answers (line, pie, bar, stacked, forecast, ANY visualisation):
     - Build a plotly.graph_objects.Figure (or plotly.express figure)
     - You MUST print its JSON between markers, EACH ON ITS OWN LINE:
           print('<<<CHART_START>>>')
           print(fig.to_json())
           print('<<<CHART_END>>>')
     - DO NOT call fig.show(), fig.write_html(), or fig.write_image().
     - DO NOT save files. The ONLY way to return a chart is fig.to_json() above.
5. For FORECASTS that say "for every Model": loop over every model_id and
   produce a SINGLE figure with one trace per model.
6. Use Polars when reasonable for transforms; convert to pandas only at chart time.
7. Polars API cheatsheet (use these EXACT signatures, NOT pandas equivalents):
     - Sort:        df.sort('col', descending=True)        # NOT reverse=True
     - Group:       df.group_by('col').agg(pl.len().alias('count'))   # NOT pl.count()
     - Count rows:  pl.len()                               # NOT pl.count()
     - Filter:      df.filter(pl.col('x') > 5)
     - Datetime:    pl.col('created_at').dt.weekday()      # 1=Mon..7=Sun
     - Date only:   pl.col('created_at').dt.date()
     - Strftime:    pl.col('created_at').dt.strftime('%A') # 'Monday' etc.
     - To pandas:   df.to_pandas()
   Prophet requires columns named 'ds' and 'y'. Statsmodels accepts a pandas Series.
8. Always handle empty data gracefully -- print 'NO_DATA' if the result set is empty.
9. The script must be runnable as-is via `python script.py` with no edits.
10. Do NOT include `if __name__ == "__main__":` -- the code runs at top level.
11. Always end your script with: import sys; sys.stdout.flush()
12. NEVER print bytes objects. If you have bytes, decode them with .decode() first.

Available libraries: polars, pandas, sqlalchemy, plotly, prophet, statsmodels.
"""


@dataclass
class GeneratedCode:
    code: str
    output_kind: str  # 'text', 'chart', or 'mixed'


def _strip_code_fences(text: str) -> str:
    """Remove ``` fences if the LLM ignored instructions and added them anyway."""
    text = text.strip()
    fence_match = re.match(r"^```(?:python)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def _classify_output_kind(question: str) -> str:
    q = question.lower()
    chart_keywords = (
        "chart", "plot", "graph", "forecast", "visual", "pie", "bar",
        "line", "stacked", "stack", "trend", "histogram",
    )
    if any(k in q for k in chart_keywords):
        return "chart"
    return "text"


def generate_python_code(question: str) -> GeneratedCode:
    """Use LlamaIndex + GPT-4o-mini to produce a Python script for the question."""
    cfg = get_config()
    if not cfg.has_openai:
        raise RuntimeError("OPENAI_API_KEY is missing. Cannot call the LLM.")

    llm = OpenAI(model=cfg.openai_model, api_key=cfg.openai_api_key, temperature=0)
    messages = [
        ChatMessage(role="system", content=CODE_GEN_SYSTEM_PROMPT),
        ChatMessage(role="user", content=question),
    ]
    response = llm.chat(messages)
    raw = response.message.content or ""
    code = _strip_code_fences(raw)
    return GeneratedCode(code=code, output_kind=_classify_output_kind(question))
