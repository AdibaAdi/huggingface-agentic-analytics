# Hugging Face Agentic Analytics: Source Guide

End to end agentic analytics over Hugging Face model and discussion data.

* **Frontend:** Streamlit, with one page for each major view.
* **Agent:** LlamaIndex plus GPT 4o mini generates a Python script at runtime
  in response to a natural language question.
* **Execution:** the user picks one of four sandboxes for every prompt
  (Bonus 2 requirement):
  1. LlamaIndex Code Interpreter (`CodeInterpreterToolSpec`)
  2. Docker Python Sandbox (`python:3.11-slim` container)
  3. OpenAI Hosted Code Execution (Assistants API plus Code Interpreter)
  4. E2B Cloud Sandbox (`e2b-code-interpreter`)
* **Storage:** PostgreSQL, populated by the ETL pipeline under `src/etl/`.
* **Output:** textual answers, tabular CSV, and Plotly charts (line, pie,
  bar, stacked bar, Prophet forecasts, Statsmodels forecasts).

## Architecture diagram

```text
Streamlit UI (natural language prompt)
        |
        v
LlamaIndex agent (GPT 4o mini) -> generated Python script
        |
        v
Sandbox selector (one of four)
        |
        v
PostgreSQL  <---  ETL pipeline  <---  Hugging Face Hub API
        |
        v
stdout (CSV table markers + Plotly JSON markers)
        |
        v
Streamlit renders answer, table, chart
```

## Prerequisites

* Python 3.11
* PostgreSQL 14 or newer running locally or reachable from your host
* Docker Desktop (only required if you select the Docker sandbox)
* Accounts and API keys:
  * OpenAI (`OPENAI_API_KEY`)
  * Hugging Face read token (`HUGGINGFACE_API_TOKEN`)
  * E2B (`E2B_API_KEY`) for the E2B sandbox only

## Install

```bash
# From the repository root, create and activate a Python 3.11 environment.
uv venv --python 3.11
source .venv/bin/activate

# Install all dependencies.
uv pip install -r src/requirements.txt
```

## Configure

Create `.env` at the repository root (NOT inside `src/`):

```dotenv
DATABASE_URL=postgresql+psycopg2://YOUR_USER:YOUR_PASSWORD@localhost:5432/hf_analytics
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
HUGGINGFACE_API_TOKEN=hf_...
E2B_API_KEY=e2b_...
TOP_N_PER_TAG=5
```

Create the database once:

```bash
createdb -U YOUR_USER hf_analytics
# or with Docker:
docker run --name hf-postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=hf_analytics -p 5432:5432 -d postgres:16
```

If you want to inspect or apply the schema by hand instead of letting
SQLAlchemy create it, run:

```bash
psql -d hf_analytics -f sql/01_create_tables.sql
psql -d hf_analytics -f sql/02_cleaning_views.sql
```

## Step by step run

### 1. Run the ETL pipeline

From the repository root:

```bash
python -m src.etl.run_pipeline
```

A successful run prints a JSON summary similar to:

```json
{
  "models_seen": 25,
  "models_cleaned": 25,
  "models_loaded": 25,
  "discussions_seen": 1300,
  "discussions_cleaned": 1300,
  "discussions_loaded": 1300,
  "fetch_errors": []
}
```

Some repositories (for example `pyannote/speaker-diarization-3.1`) return a
403 on discussions because the maintainer has disabled them. Those repos
are logged in `fetch_errors` and skipped safely.

### 2. Verify the data

```bash
psql -d hf_analytics -c "SELECT tag, COUNT(*) FROM model_repos GROUP BY tag;"
psql -d hf_analytics -c "SELECT status, COUNT(*) FROM discussions GROUP BY status;"
```

### 3. (Optional) Prebuild the Docker sandbox image

The Streamlit app builds it on demand, but you can prebuild it for a faster
first run:

```bash
docker build -t hf-bonus-sandbox:latest -f - . <<'EOF'
FROM python:3.11-slim
RUN pip install --no-cache-dir polars==1.* pandas plotly sqlalchemy \
    psycopg2-binary prophet 'statsmodels==0.14.5'
WORKDIR /work
EOF
```

### 4. Launch the Streamlit app

```bash
streamlit run src/app/streamlit_app.py
```

### 5. Use it

1. Pick a backend in the sidebar (start with **LlamaIndex Code Interpreter**
   for fast local iteration).
2. Open the **Agentic Analytics** page.
3. Type a natural language question in the text area.
4. Click **Generate code and execute**.
5. The app shows the LLM generated Python, runs it in your chosen sandbox,
   and renders the resulting text, table, and chart output.

Other pages in the sidebar give static views:

* **Executive Summary** for headline findings.
* **Top Models** for the composite engagement ranking.
* **Anomaly Detection** for unusual discussion spikes.
* **Forecasting** for Prophet and Statsmodels forecasts.
* **Data Quality** for row level validation.
* **Methodology** for the written methodology and limitations.

### 6. (Bonus 2) Run the comparative analysis

To reproduce the comparison table in `doc/comparative_analysis_report.md`:

```bash
python -m src.app.run_comparative_analysis
```

This sends six prompts through all four backends and writes
`doc/comparative_analysis.json`.

### 7. Run the tests

```bash
pytest tests/
```

## Required prompts (assignment checklist)

Type these verbatim into the Streamlit text box on the Agentic Analytics
page.

### Text and table

* Which Hugging Face model repo has the highest number of Community Discussions created?
* Create a table of the total number of Discussions created for every repo for every day of the week (Monday-Sunday).
* Which day of the week has the highest number of total Discussions created across all tracked Hugging Face repos?
* Which day of the week has the highest number of total Discussions marked as 'Closed' for all Hugging Face repos?

### Charts

* Line chart: total Discussions over time across all models.
* Pie chart: percentage distribution of total Discussions belonging to each model.
* Bar chart: Likes count for every Model ID.
* Bar chart: Downloads for every Model ID (used as a forks proxy).
* Bar chart: closed Discussions per week.
* Stacked bar chart: open vs closed Discussions for every Model.
* Use Prophet to forecast created Discussions for every Model.
* Use Prophet to forecast closed Discussions for every Model.
* Use Statsmodels to forecast Pull Requests for every Model.
* Use Statsmodels to forecast Commits for every Model.

## File map

| Path | Purpose |
| --- | --- |
| `src/config.py` | Loads `.env`, exposes typed config. |
| `src/db.py` | SQLAlchemy ORM models and engine. |
| `src/etl/extract_hf_models.py` | Fetches top N Hugging Face models per tag. |
| `src/etl/extract_discussions.py` | Fetches community discussions per repo. |
| `src/etl/transform_clean.py` | Pure cleaning functions used by the pipeline and the tests. |
| `src/etl/load_postgres.py` | Idempotent upserts into PostgreSQL. |
| `src/etl/run_pipeline.py` | End to end ETL orchestrator. |
| `src/analysis/sql_queries.py` | Canned SQL queries exposed as helpers. |
| `src/analysis/model_metrics.py` | Composite engagement score and top N. |
| `src/analysis/anomaly_detection.py` | Rolling baseline spike detector. |
| `src/analysis/forecasting.py` | Prophet and Statsmodels forecasts. |
| `src/analysis/data_quality.py` | Row level validation checks. |
| `src/app/streamlit_app.py` | Multi page Streamlit dashboard. |
| `src/app/code_generator.py` | LlamaIndex agent that turns NL into Python. |
| `src/app/output_parser.py` | Extracts CSV tables and Plotly JSON from stdout. |
| `src/app/sandboxes.py` | The four code execution backends (Bonus 2). |
| `src/app/run_comparative_analysis.py` | Bonus 2 reproducible benchmark runner. |
| `src/utils/logging_utils.py` | Small logger factory. |
| `sql/01_create_tables.sql` | Hand applicable schema. |
| `sql/02_cleaning_views.sql` | Reusable cleaning views. |
| `sql/03_analysis_queries.sql` | Reproducible analysis queries. |
| `tests/` | Pytest suite for transformations, validation, and parsing. |

## Troubleshooting

* **`OPENAI_API_KEY is missing`** - `.env` is not at the repository root, or
  the shell is reading a different file. Confirm with `env | grep OPENAI`.
* **Docker backend cannot reach Postgres** - the generated code uses
  `host.docker.internal` automatically. Make sure Postgres listens on
  `0.0.0.0` (`listen_addresses = '*'` in `postgresql.conf`), and that
  `pg_hba.conf` allows a rule for `host.docker.internal` or `172.17.0.0/16`.
* **OpenAI Hosted timeout** - large datasets take longer to upload as CSV.
  Try a more specific prompt or switch backends.
* **E2B "API key invalid"** - verify at https://e2b.dev/dashboard.
* **Prophet first run is slow** - Prophet compiles a Stan model on first
  use. This is a one time cost per Python environment.
