# Panopto Demo Script (5 to 10 minutes)

A suggested walkthrough for the recorded live demo. Times are rough; aim
for clarity over hitting exact minute marks.

## 1. Intro (45 seconds)

* "This is Hugging Face Agentic Analytics, my class project for Bonus
  Assignment 1 and Bonus Assignment 2."
* "It pulls top Hugging Face models by tag, stores model and discussion
  data in PostgreSQL, and answers natural language questions with text,
  tables, and charts in a Streamlit app."
* "It also implements the Bonus 2 requirement: a single agent backed by
  four hot swappable code execution sandboxes."

## 2. Architecture walkthrough (90 seconds)

* Show the root `README.md` architecture section.
* Walk through the diagram: Streamlit prompt, LlamaIndex agent generates
  Python, sandbox selector runs it, marker delimited stdout flows back to
  the app, which renders tables and charts.
* Mention the stack: Python 3.11, Polars, PostgreSQL with SQLAlchemy,
  Hugging Face Hub API, LlamaIndex plus GPT 4o mini, Prophet and
  Statsmodels for forecasting, Plotly for charts.

## 3. Environment setup (60 seconds)

* Show `.env.example` and explain required keys:
  * `DATABASE_URL`
  * `OPENAI_API_KEY`
  * `HUGGINGFACE_API_TOKEN` (optional but recommended)
  * `E2B_API_KEY` (optional)
* Confirm no real keys are committed.
* Show `src/requirements.txt` and the `uv pip install -r src/requirements.txt`
  command.

## 4. Ingestion demo (90 seconds)

* From the repo root, run `python -m src.etl.run_pipeline`.
* While it runs, walk through the ETL split: extract, transform, load.
* When it finishes, show the JSON summary: how many models and
  discussions were loaded, and any per repo errors (typically a 403 for
  repos with discussions disabled).

## 5. Streamlit app demo (2 to 3 minutes)

* Run `streamlit run src/app/streamlit_app.py`.
* Show the sidebar with setup status and ingestion button.
* Visit the **Executive Summary** page and call out the headline
  metrics.
* Visit **Agentic Analytics**:
  * Pick a backend in the dropdown.
  * Paste the first required text or table prompt verbatim.
  * Show the generated Python code in the expander.
  * Show the rendered table or chart.
  * Repeat for one chart prompt and one forecast prompt.
* Briefly visit **Top Models**, **Anomaly Detection**, **Forecasting**,
  and **Data Quality** so reviewers see they exist.

## 6. Bonus Assignment 2 demo (90 seconds)

* On the Agentic Analytics page, run the same prompt through two
  different sandboxes back to back. Point out that the answer is
  identical but the elapsed time differs.
* Open `doc/comparative_analysis_report.md` and read the recommendations
  section out loud.
* If time permits, run `python -m src.app.run_comparative_analysis` to
  demonstrate that the comparison is reproducible.

## 7. Tests and methodology (45 seconds)

* From the repo root, run `pytest tests/` and show the green test count.
* Open `doc/methodology.md` and `doc/limitations.md` to demonstrate that
  the project is documented for non technical reviewers.

## 8. Close (20 seconds)

* "This project takes both Bonus assignments seriously and adds a
  reproducible analyst layer on top: documented methodology, data
  quality validation, anomaly detection, executive summary, and tests."
* "Thanks for watching."
