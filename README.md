# huggingface-agentic-analytics

A first working version of a class project for **Bonus Assignment 1** and **Bonus Assignment 2**.

## Project overview
This app ingests top Hugging Face model repositories and discussions by tag, stores them in PostgreSQL, then serves a Streamlit interface for natural-language analytics (text + table + charts).

## Architecture
- **Frontend:** Streamlit (`src/app.py`)
- **Agent routing:** LangChain + GPT-4o-mini with deterministic fallback (`src/langchain_agent.py`)
- **Data layer:** PostgreSQL + SQLAlchemy ORM (`src/db.py`)
- **Ingestion:** Hugging Face Hub API (`src/ingest_hf_data.py`)
- **Analytics:** Deterministic Polars queries (`src/analytics_queries.py`)
- **Charts:** Plotly + Prophet + Statsmodels fallback charts (`src/charts.py`)
- **Safe execution utility:** constrained executor (`src/code_executor.py`)
- **Bonus 2 alternatives:** LlamaIndex/Docker/OpenAI/E2B module (`src/bonus2_llamaindex_alternatives.py`)

## Setup steps
1. Install Python 3.11.
2. Create virtual environment.
3. Install requirements:
   ```bash
   uv pip install -r src/requirements.txt
   ```
4. Copy env template and edit values:
   ```bash
   cp .env.example .env
   ```

## .env configuration
Set these values in `.env`:
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default `gpt-4o-mini`)
- `HF_TOKEN` (optional)
- `E2B_API_KEY` (optional)
- `TOP_N_PER_TAG` (default 5)

## Run PostgreSQL locally
Example using Docker:
```bash
docker run --name hf-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=hf_analytics -p 5432:5432 -d postgres:16
```

## Run ingestion
```bash
python src/ingest_hf_data.py
```

## Run Streamlit
```bash
streamlit run src/app.py
```

## Run Bonus 2 alternatives
```bash
python -c "from src.bonus2_llamaindex_alternatives import demo_all_alternatives; print(demo_all_alternatives())"
```

## Known limitations
- Hugging Face discussion endpoints may not provide full GitHub-style forks/commit/PR timelines per repo.
- This project uses fallback logic:
  - **Downloads** as forks replacement metric.
  - **`is_pull_request` discussion flag** when available for PR-like analysis.
  - **Discussion activity fallback** for commit-related forecast chart.
- If API keys are missing, app shows warnings and uses deterministic routing fallback.
