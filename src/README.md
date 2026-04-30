# Hugging Face Agentic Analytics — Bonus 2

End-to-end agentic analytics over Hugging Face model + discussion data.

- **Frontend:** Streamlit free-text natural-language prompt
- **Agent:** LlamaIndex + GPT-4o-mini generates Python code at runtime
- **Execution:** user picks ONE of four sandboxes (Bonus 2 requirement):
  1. **LlamaIndex Code Interpreter** (`CodeInterpreterToolSpec`)
  2. **Docker Python Sandbox** (`python:3.11-slim` container)
  3. **OpenAI Hosted Code Execution** (Assistants API + Code Interpreter tool)
  4. **E2B Cloud Sandbox** (`e2b-code-interpreter`)
- **Storage:** Postgres (top-5 models per HF tag + their Discussions)
- **Output:** textual answers, tabular CSV, and Plotly charts (line, pie, bar,
  stacked bar, Prophet forecasts, Statsmodels forecasts)

## Architecture

```
Streamlit prompt
      │ (natural language)
      ▼
LlamaIndex agent (GPT-4o-mini)
      │ (generated Python script)
      ▼
[ User picks 1 of 4 ]
      │
 ┌────┼────┬─────────────┬──────────────┐
 ▼    ▼    ▼             ▼              ▼
LI-CI Docker  OpenAI-Hosted   E2B-Cloud
      │     │             │              │
      └─────┴──────┬──────┴──────────────┘
                   ▼
             stdout (CSV table + chart JSON)
                   ▼
             Streamlit renders
```

## Prerequisites

- Python 3.11
- PostgreSQL 14+ running locally (or reachable host)
- Docker Desktop (only required if you select the Docker sandbox)
- Accounts/API keys:
  - OpenAI (`OPENAI_API_KEY`)
  - Hugging Face read token (`HUGGINGFACE_API_TOKEN`)
  - E2B (`E2B_API_KEY`) — only required for E2B sandbox

## Install

```bash
# Use a Python 3.11 venv
uv venv --python 3.11
source .venv/bin/activate

# Install all deps
uv pip install -r src/requirements.txt
```

## Configure

Create `.env` at the repository root (NOT inside `src/`):

```dotenv
DATABASE_URL=postgresql+psycopg2://YOUR_USER@localhost:5432/hf_bonus_db
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
HUGGINGFACE_API_TOKEN=hf_...
E2B_API_KEY=e2b_...
TOP_N_PER_TAG=5
```

Create the database once:
```bash
createdb -U YOUR_USER hf_bonus_db
```

## Step-by-step run

### 1. Ingest Hugging Face data into Postgres

```bash
python src/ingest_hf_data.py
```

You should see something like:
```
- models_seen: 25
- models_inserted_or_updated: 25
- discussions_inserted_or_updated: 1300+
```

(One repo `pyannote/speaker-diarization-3.1` may 403 on discussions — this
is a repo-level setting on HF and is safely skipped.)

### 2. Verify data

```bash
psql -d hf_bonus_db -c "SELECT tag, COUNT(*) FROM model_repos GROUP BY tag;"
psql -d hf_bonus_db -c "SELECT status, COUNT(*) FROM discussions GROUP BY status;"
```

### 3. (Optional) Build the Docker sandbox image once

The Streamlit app builds it automatically the first time you select the
Docker backend, but you can prebuild for faster first run:

```bash
docker build -t hf-bonus-sandbox:latest -f - . <<'EOF'
FROM python:3.11-slim
RUN pip install --no-cache-dir polars==1.* pandas plotly sqlalchemy \
    psycopg2-binary prophet 'statsmodels==0.14.5'
WORKDIR /work
EOF
```

### 4. Launch Streamlit

```bash
streamlit run src/app.py
```

### 5. Use it

1. Pick a backend in the sidebar (start with **LlamaIndex Code Interpreter**
   for fast local iteration).
2. Type a natural-language question in the text area.
3. Click **🚀 Generate code and execute**.
4. The app shows the LLM-generated Python, runs it in your chosen sandbox,
   and renders the resulting text/table/chart.

### 6. (Bonus 2) Run the comparative analysis

To reproduce the comparison table in `doc/comparative_analysis_report.md`:

```bash
python src/run_comparative_analysis.py
```

This runs 6 prompts through all 4 backends and writes
`doc/comparative_analysis.json`.

## Required prompts (assignment checklist)

Type these verbatim in the Streamlit text box.

**Text/table:**
- Which Hugging Face model repo has the highest number of Community Discussions created?
- Create a table of the total number of Discussions created for every repo for every day of the week (Monday-Sunday).
- Which day of the week has the highest number of total Discussions created across all tracked Hugging Face repos?
- Which day of the week has the highest number of total Discussions marked as 'Closed' for all Hugging Face repos?

**Charts:**
- Line chart: total Discussions over time across all models.
- Pie chart: % distribution of total Discussions belonging to each model.
- Bar chart: Likes count for every Model ID.
- Bar chart: Downloads for every Model ID (forks proxy).
- Bar chart: Closed Discussions per week.
- Stacked bar chart: open vs closed Discussions for every Model.
- Use Prophet to forecast created Discussions for every Model.
- Use Prophet to forecast closed Discussions for every Model.
- Use Statsmodels to forecast Pull Requests for every Model.
- Use Statsmodels to forecast Commits for every Model.

## File map

| File | Purpose |
|---|---|
| `config.py` | Loads `.env`, exposes typed config |
| `db.py` | SQLAlchemy ORM models + engine |
| `ingest_hf_data.py` | Pulls top-N HF models/discussions → Postgres |
| `code_generator.py` | LlamaIndex agent: NL → Python script |
| `sandboxes.py` | 4 sandbox backends (Bonus 2) |
| `output_parser.py` | Extracts CSV tables + Plotly JSON from stdout |
| `app.py` | Streamlit UI |
| `run_comparative_analysis.py` | Runs prompts × 4 backends → JSON report |
| `requirements.txt` | uv pip install dependencies |

## Troubleshooting

- **`OPENAI_API_KEY is missing`** — `.env` not at repo root, or wrong shell.
- **Docker backend "Cannot connect to localhost"** — code uses
  `host.docker.internal` automatically; make sure your Postgres listens on
  `0.0.0.0` not just `127.0.0.1` (Postgres `listen_addresses = '*'` in
  `postgresql.conf`, plus a `pg_hba.conf` rule for `host.docker.internal`
  / `172.17.0.0/16`).
- **OpenAI Hosted timeout** — large datasets take longer to upload as CSV.
  Try a more specific prompt or use a different backend.
- **E2B "API key invalid"** — verify at https://e2b.dev/dashboard.
