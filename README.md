# Hugging Face Agentic Analytics

A reproducible Python data pipeline and agentic analytics application that collects Hugging Face model and discussion metadata via the public Hub API, cleans and validates the data, stores it in PostgreSQL, and supports natural language analytical questions answered with text, tables, and Plotly visualizations.

This project was originally built for **CS 487 Bonus Assignments 1 and 2** and was extended into a portfolio grade data analyst case study covering ETL, SQL aggregation, data quality validation, anomaly detection, time series forecasting, and clear methodology and limitations documentation.

## Highlights

- **End to end ETL** from the Hugging Face Hub API into a normalized PostgreSQL schema with primary keys, foreign keys, and uniqueness constraints.
- **Reusable SQL layer** with cleaning views and analysis views that power the dashboard and the reproducible report.
- **Agentic natural language interface** built on LlamaIndex plus GPT 4o mini. The agent writes Python at runtime against the documented schema; the user picks one of four execution backends.
- **Four interchangeable code execution sandboxes** (Bonus Assignment 2): LlamaIndex Code Interpreter, Docker Python sandbox, OpenAI Hosted Code Execution, and E2B Cloud Sandbox. A single output protocol parses CSV tables and Plotly JSON from stdout, so all four backends are hot swappable.
- **Data quality validation** with row level checks for duplicates, nulls, invalid statuses, and impossible timestamps, surfaced in the Streamlit Data Quality page.
- **Investigation oriented analysis** including weekly closure rates, model engagement scoring, and a rolling baseline anomaly detector for unusual discussion spikes.
- **Forecasting** with Prophet (created and closed discussions) and Statsmodels Exponential Smoothing (pull request like activity and commit proxy).
- **Methodology, data dictionary, and limitations** documented in `doc/` for non technical readers.
- **Tests** for the ETL transformations and data quality checks.

## Architecture

```text
Streamlit UI (user question in natural language)
        |
        v
LlamaIndex agent + GPT 4o mini (generates Python script)
        |
        v
Sandbox selector (one of four backends)
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

## Repository layout

The top level layout follows the assignment specification (`src/` and `doc/` directories) while the contents of `src/` are organized as a data analyst portfolio project.

```text
huggingface-agentic-analytics/
  README.md
  .env.example
  src/
    requirements.txt
    README.md
    config.py
    db.py
    etl/
      extract_hf_models.py
      extract_discussions.py
      transform_clean.py
      load_postgres.py
      run_pipeline.py
    analysis/
      sql_queries.py
      model_metrics.py
      anomaly_detection.py
      forecasting.py
      data_quality.py
    app/
      streamlit_app.py
      code_generator.py
      output_parser.py
      sandboxes.py
    utils/
      logging_utils.py
  sql/
    01_create_tables.sql
    02_cleaning_views.sql
    03_analysis_queries.sql
  tests/
    test_transform_clean.py
    test_data_quality.py
    test_output_parser.py
  doc/
    methodology.md
    data_dictionary.md
    limitations.md
    comparative_analysis_report.md
    executive_summary.md
    demo_script.md
    code_sample_cover_sheet.md
    panopto_video_link.txt
    screenshots/
```

## Quick start

Full setup, ingestion, and demo instructions live in `src/README.md`. The short version:

```bash
# 1. Python 3.11 environment
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r src/requirements.txt

# 2. Configure
cp .env.example .env       # then fill in your keys

# 3. Start a local Postgres (Docker example)
docker run --name hf-postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=hf_analytics -p 5432:5432 -d postgres:16

# 4. Run the ETL pipeline
python -m src.etl.run_pipeline

# 5. Launch the Streamlit app
streamlit run src/app/streamlit_app.py
```

## Documentation index

| Document | What it covers |
| --- | --- |
| `doc/methodology.md` | End to end methodology of data collection, cleaning, storage, and analysis. |
| `doc/data_dictionary.md` | Field by field definitions for every table and view. |
| `doc/limitations.md` | Honest description of what the dataset and analysis cannot tell you. |
| `doc/executive_summary.md` | Key findings written for a non technical reader. |
| `doc/comparative_analysis_report.md` | Bonus 2 deliverable: comparison of the four code execution backends. |
| `doc/code_sample_cover_sheet.md` | One page cover sheet for use as a writing or code sample. |
| `doc/demo_script.md` | Panopto recording walkthrough script. |
| `doc/panopto_video_link.txt` | Final recording URL (filled in before submission). |

## What this project demonstrates

- API based data extraction from a public web API with paginated discussion endpoints.
- PostgreSQL schema design with constraints, foreign keys, and indexed lookups.
- Reproducible Python ETL with idempotent upserts.
- Data quality validation surfaced in a dashboard.
- Advanced SQL aggregation including window functions and conditional aggregates.
- Time series forecasting with two different libraries (Prophet and Statsmodels).
- A multi backend code execution architecture used to compare sandbox approaches.
- Clear written methodology, limitations, and findings.
- Reproducible setup, deterministic seeds where applicable, and tests covering the most fragile transformations.

## License and attribution

Course project for educational purposes. Hugging Face data is fetched under the Hugging Face Hub terms of service. All third party libraries retain their original licenses.
