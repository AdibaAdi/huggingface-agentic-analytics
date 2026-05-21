# Methodology

This document describes how the Hugging Face Agentic Analytics dataset is
collected, cleaned, stored, and analyzed. It is written for reviewers who
want to understand the pipeline without reading the source.

## 1. Data sources

The only external data source is the public Hugging Face Hub API, accessed
through the official `huggingface_hub` Python client. No scraping is
involved. Two endpoints are used:

1. `HfApi.list_models(filter=tag, sort="downloads", limit=N, full=True)`
   returns the top N model repositories for a given category tag, ranked
   by total download count.
2. `HfApi.get_repo_discussions(repo_id, repo_type="model")` returns every
   community discussion thread (issues and pull requests) attached to a
   given repository.

## 2. Scope

The pipeline tracks the top 5 model repositories in each of the following
Hugging Face tags:

* `text-generation`
* `image-text-to-text`
* `text-classification`
* `summarization`
* `automatic-speech-recognition`

This produces 25 model repositories and approximately 1,000 to 1,500
discussions in a typical run. The set is configurable through the
`hf_tags` and `top_n_per_tag` settings in `src/config.py`.

## 3. Extraction

`src/etl/extract_hf_models.py` calls `list_models` once per tag and
flattens the response into plain Python dictionaries. `src/etl/extract_discussions.py`
calls `get_repo_discussions` once per tracked repository. Failures are
caught per repository, logged, and returned alongside the successful rows
so the rest of the pipeline still completes. The most common failure is a
403 from repositories whose maintainers have disabled community
discussions; those repos are skipped.

## 4. Transformation

`src/etl/transform_clean.py` applies deterministic, locale independent
cleaning rules:

* Whitespace is stripped from all string fields.
* Status values are coerced into the canonical lowercase set
  `{"open", "closed"}`. Anything else falls back to `"open"`.
* Numeric counts (likes, downloads) are coerced to non negative integers.
* Rows missing required identifiers (`model_id`, `hf_discussion_num`) are
  dropped before load.
* A `weekday` field is derived from `created_at` using Python's
  `datetime.weekday()` and the canonical English names, so weekday
  aggregations are reproducible regardless of database locale.

These functions are pure and easy to unit test. See `tests/test_transform_clean.py`.

## 5. Storage

Data is stored in two PostgreSQL tables, `model_repos` and `discussions`,
defined in `src/db.py` and mirrored in `sql/01_create_tables.sql`. The
schema enforces:

* `model_repos.model_id` is unique.
* `discussions.(repo_id, hf_discussion_num)` is unique.
* `discussions.repo_id` is a foreign key to `model_repos.id`.

These constraints let the ETL pipeline upsert rows safely, so it can run
many times without producing duplicates.

Two reusable views support analysis (`sql/02_cleaning_views.sql`):

* `v_discussions_clean` joins each discussion to its parent repository and
  adds derived columns (`weekday_created`, `weekday_closed`, `is_closed`).
* `v_model_discussion_summary` aggregates per repository totals and
  closure rate.

## 6. Analysis layer

Three layers of analysis sit on top of the database:

1. **Canned SQL queries** in `src/analysis/sql_queries.py`. Every Python
   helper mirrors a query in `sql/03_analysis_queries.sql`, so the
   dashboard and the written report cannot drift from each other.
2. **Composite metrics** in `src/analysis/model_metrics.py`. The
   engagement score is the unweighted mean of three min max normalized
   columns: downloads, likes, and total discussions. It is bounded in
   `[0, 1]`. Closure rate is closed discussions divided by total
   discussions per repository.
3. **Investigation tools** in `src/analysis/anomaly_detection.py`. A day
   is flagged as a spike when its discussion count is at least `multiplier`
   times the trailing rolling mean (default window 7 days, multiplier 2.0).
   The detector is intentionally simple: it surfaces obvious unusual
   activity, not statistical anomalies.

## 7. Forecasting

`src/analysis/forecasting.py` produces two flavors of forecast:

* **Prophet** is used for created discussions and closed discussions, with
  daily seasonality enabled and a 14 day forecast horizon. Prophet's
  flexibility with holidays and trend changes is useful when discussion
  volume is bursty.
* **Statsmodels Exponential Smoothing** is used for pull request style
  activity and the commit proxy series. The additive trend model is
  enough for these shorter, smoother series and is faster to fit.

All forecasts return a single Plotly figure with one trace per repository,
so the Streamlit Forecasting page renders without backend specific code.

## 8. Agentic question answering

The Agentic Analytics page in the Streamlit app does not call any of the
canned queries above. Instead, it sends the natural language question to
a LlamaIndex agent backed by GPT 4o mini. The agent receives the explicit
PostgreSQL schema and a strict output protocol, then writes a single self
contained Python script that:

* Connects to the database via SQLAlchemy.
* Computes the answer with Polars, Pandas, Plotly, Prophet, or Statsmodels.
* Prints either a CSV table or a Plotly figure JSON between marker tags.

The user picks one of four execution sandboxes (LlamaIndex Code
Interpreter, Docker, OpenAI Hosted, E2B Cloud) at run time. The output
parser is identical across backends because all four return marker
delimited stdout. See `doc/comparative_analysis_report.md` for the
trade offs between backends.

## 9. Data quality validation

`src/analysis/data_quality.py` runs ten row level checks on each load.
Failures and informational counts are surfaced on the Data Quality page in
the Streamlit app. Validation is intentionally part of the dashboard, not
hidden in logs, so reviewers can confirm the dataset is trustworthy before
reading the analysis.

Pure validation logic is unit tested in `tests/test_data_quality.py`.

## 10. Reproducibility

* The ETL pipeline is idempotent. Re-running it does not produce duplicate
  rows.
* All randomness is deterministic. The only stochastic component is
  Prophet's MCMC sampler, which is deterministic at default settings.
* All required prompts run with temperature zero against `gpt-4o-mini`.
* `python -m src.app.run_comparative_analysis` produces a JSON record of
  every prompt run across every backend so the comparative report can be
  regenerated.
