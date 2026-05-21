# Code Sample Cover Sheet

**Title:** Hugging Face Agentic Analytics. Python ETL and SQL based
analysis of Hugging Face model and discussion data.

**Author:** Adiba

**Repository:** `huggingface-agentic-analytics`

**Languages and tools:** Python 3.11, PostgreSQL 16, SQL (window
functions, conditional aggregates, views), SQLAlchemy, Polars, Pandas,
Plotly, Prophet, Statsmodels, Streamlit, LlamaIndex, GPT 4o mini,
Docker, pytest.

## What this sample demonstrates

This code sample is a reproducible Python data pipeline that:

* Extracts Hugging Face model and discussion metadata from the public
  Hugging Face Hub API.
* Cleans and validates the data with deterministic, unit tested
  transformations.
* Loads the data into a normalized PostgreSQL schema with primary keys,
  foreign keys, and unique constraints.
* Analyzes the data using a layered SQL plus Python approach. The same
  queries are exposed in `sql/03_analysis_queries.sql` and as Python
  helpers in `src/analysis/sql_queries.py`.
* Computes composite metrics (engagement score, closure rate) and runs a
  rolling baseline anomaly detector for unusual discussion spikes.
* Forecasts created and closed discussion volume with Prophet and
  Statsmodels.
* Surfaces row level data quality validation in the Streamlit dashboard.
* Documents methodology, limitations, and findings for non technical
  readers.

In addition, the project implements an agentic question answering
interface backed by four interchangeable code execution sandboxes
(LlamaIndex Code Interpreter, Docker, OpenAI Hosted, E2B Cloud) so the
same generated Python can be executed in four different environments
without changing the agent or the UI.

## Why this sample is representative

I am submitting this sample because it reflects the skills required for
data analyst work:

* **Dataset creation:** I created the dataset from a public API rather
  than working with a pre cleaned source.
* **Data cleaning:** Deterministic, locale independent cleaning rules
  with unit tests. Status canonicalization, weekday derivation, and
  required field enforcement.
* **Reproducible methods:** Idempotent ETL, deterministic seeds where
  applicable, all secrets in `.env`, all queries checked in.
* **SQL fluency:** Conditional aggregates, joins, views, and a window
  function example in `sql/03_analysis_queries.sql`.
* **Visualization:** Plotly charts driven by the same data layer the
  written analysis uses, so the dashboard and the report cannot drift.
* **Investigation oriented analysis:** Closure rate, engagement ranking,
  and rolling baseline spike detection support the kind of pattern
  finding work an investigative analyst would do.
* **Clear communication:** `doc/methodology.md`,
  `doc/data_dictionary.md`, `doc/limitations.md`, and
  `doc/executive_summary.md` are written for non technical readers.
* **Version control:** The project is structured for Git and follows
  standard Python project conventions (`src/`, `tests/`, `requirements.txt`,
  `.env.example`).

## How to read the sample

If you have ten minutes:

1. Read this cover sheet and `doc/executive_summary.md`.
2. Skim the top level `README.md` for the architecture diagram and
   directory layout.

If you have thirty minutes:

3. Read `doc/methodology.md` and `doc/limitations.md`.
4. Open `src/etl/transform_clean.py` and the matching
   `tests/test_transform_clean.py` to see the cleaning logic and tests.
5. Open `sql/03_analysis_queries.sql` to see the SQL.

If you want to run it:

6. Follow the quick start in the top level `README.md`. The project
   ships with a pinned `requirements.txt`, an `.env.example`, and
   reproducible step by step instructions in `src/README.md`.
