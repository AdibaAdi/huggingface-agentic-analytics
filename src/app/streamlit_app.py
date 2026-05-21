"""Streamlit application entry point.

The app is organized into pages that mirror how a data analyst would
present this work to a non technical reader:

* Executive Summary  - the headline findings.
* Agentic Analytics  - the natural language question interface, with the
  Bonus 2 sandbox selector.
* Top Models         - composite engagement table.
* Anomaly Detection  - flagged discussion spikes.
* Forecasting        - Prophet and Statsmodels forecasts.
* Data Quality       - row level validation results.
* Methodology        - written methodology and limitations.

Run from the repository root:

    streamlit run src/app/streamlit_app.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Ensure ``src`` is on the path no matter how Streamlit invokes the file.
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import plotly.io as pio  # noqa: E402
import streamlit as st  # noqa: E402

from analysis import (  # noqa: E402
    anomaly_detection,
    data_quality,
    forecasting,
    model_metrics,
    sql_queries,
)
from app.code_generator import generate_python_code  # noqa: E402
from app.output_parser import parse_stdout  # noqa: E402
from app.sandboxes import SANDBOXES, get_sandbox  # noqa: E402
from config import get_config  # noqa: E402
from etl.run_pipeline import run as run_pipeline  # noqa: E402

st.set_page_config(
    page_title="Hugging Face Agentic Analytics",
    page_icon="🤗",
    layout="wide",
)
cfg = get_config()

# ---------------------------------------------------------------------------
# Sidebar: status, ingestion, page selector
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🤗 HF Analytics")
    st.caption(
        "Hugging Face model and discussion analytics. "
        "Agentic code generation plus a four backend sandbox."
    )

    st.subheader("Setup status")
    st.write(f"DATABASE_URL: {'ok' if cfg.database_url else 'missing'}")
    st.write(f"OPENAI_API_KEY: {'ok' if cfg.has_openai else 'missing'}")
    st.write(f"HUGGINGFACE_API_TOKEN: {'ok' if cfg.has_hf_token else 'missing'}")
    st.write(f"E2B_API_KEY: {'ok' if cfg.has_e2b else 'missing'}")

    st.subheader("Ingestion")
    if st.button("Run the ETL pipeline now"):
        with st.spinner("Extracting, cleaning, loading..."):
            try:
                summary = run_pipeline()
                st.success("Pipeline finished")
                st.json(summary)
            except Exception as exc:
                st.error(f"Pipeline failed: {exc}")

    st.subheader("Page")
    page = st.radio(
        "Choose a view",
        [
            "Executive Summary",
            "Agentic Analytics",
            "Top Models",
            "Anomaly Detection",
            "Forecasting",
            "Data Quality",
            "Methodology",
        ],
        index=1,
    )


# ---------------------------------------------------------------------------
# Page: Executive Summary
# ---------------------------------------------------------------------------
def page_executive_summary() -> None:
    st.title("Executive Summary")
    st.write(
        "This page summarizes the headline findings produced by the pipeline "
        "and the analysis layer. Numbers update automatically when the "
        "underlying database is re-ingested."
    )

    try:
        df_top = sql_queries.repo_with_highest_discussions()
        df_created = sql_queries.day_with_most_created()
        df_closed = sql_queries.day_with_most_closed()
        df_closure = sql_queries.closure_rate_by_repo()
        df_engagement = model_metrics.top_n_by_engagement(n=10)
    except Exception as exc:
        st.error(f"Could not query the database. Have you run the ETL pipeline? {exc}")
        return

    cols = st.columns(3)
    if not df_top.empty:
        cols[0].metric(
            "Repo with most discussions",
            df_top.iloc[0]["model_id"],
            f"{int(df_top.iloc[0]['discussion_count'])} discussions",
        )
    if not df_created.empty:
        cols[1].metric(
            "Busiest weekday for new discussions",
            str(df_created.iloc[0]["weekday"]),
            f"{int(df_created.iloc[0]['total_discussions'])} total",
        )
    if not df_closed.empty:
        cols[2].metric(
            "Busiest weekday for closures",
            str(df_closed.iloc[0]["weekday"]),
            f"{int(df_closed.iloc[0]['closed_discussions'])} closed",
        )

    st.markdown("### Key findings")
    findings = []
    if not df_top.empty:
        findings.append(
            f"The repo with the most community activity is "
            f"**{df_top.iloc[0]['model_id']}** with "
            f"{int(df_top.iloc[0]['discussion_count'])} discussions tracked."
        )
    if not df_created.empty:
        findings.append(
            f"New discussions peak on **{str(df_created.iloc[0]['weekday'])}** "
            f"({int(df_created.iloc[0]['total_discussions'])} across all repos)."
        )
    if not df_closed.empty:
        findings.append(
            f"Discussion closures peak on **{str(df_closed.iloc[0]['weekday'])}**, "
            f"which suggests maintainers triage in batches."
        )
    if not df_closure.empty:
        top_closure = df_closure.dropna(subset=["closure_rate"]).head(1)
        if not top_closure.empty:
            findings.append(
                f"Highest closure rate observed: "
                f"**{top_closure.iloc[0]['model_id']}** at "
                f"{top_closure.iloc[0]['closure_rate']:.0%}."
            )
    findings.append(
        "Downloads and discussion volume are only loosely correlated; "
        "popular models do not always generate the most community traffic."
    )
    for i, finding in enumerate(findings, start=1):
        st.markdown(f"{i}. {finding}")

    st.markdown("### Top 10 repos by engagement score")
    st.caption(
        "Engagement score is the mean of three min max normalized columns: "
        "downloads, likes, and total discussions. See Methodology for details."
    )
    st.dataframe(df_engagement, use_container_width=True)


# ---------------------------------------------------------------------------
# Page: Agentic Analytics
# ---------------------------------------------------------------------------
def page_agentic_analytics() -> None:
    st.title("Agentic Analytics")
    st.caption(
        "Type a natural language question. The LlamaIndex agent writes Python "
        "against the documented schema, the chosen sandbox executes it, and "
        "this page renders the result."
    )

    sandbox_label = st.selectbox(
        "Code execution backend (Bonus 2)",
        list(SANDBOXES.keys()),
        index=0,
        help="Choose which of the four alternatives executes the generated code.",
    )

    with st.expander("Example prompts", expanded=False):
        st.markdown(
            """
**Text and table prompts**

- Which Hugging Face model repo has the highest number of Community Discussions created?
- Create a table of the total number of Discussions created for every repo for every day of the week (Monday-Sunday).
- Which day of the week has the highest number of total Discussions created across all tracked Hugging Face repos?
- Which day of the week has the highest number of total Discussions marked as 'Closed' for all Hugging Face repos?

**Chart prompts**

- Line chart: total Discussions over time across all models.
- Pie chart: percentage distribution of total Discussions belonging to each model.
- Bar chart: Likes count for every Model ID.
- Bar chart: Downloads for every Model ID (used as a forks proxy).
- Bar chart: closed Discussions per week.
- Stacked bar chart: open vs closed Discussions for every Model.
- Use Prophet to forecast created Discussions for every Model.
- Use Prophet to forecast closed Discussions for every Model.
- Use Statsmodels to forecast Pull Requests for every Model.
- Use Statsmodels to forecast Commits for every Model.
            """
        )

    question = st.text_area(
        "Your question",
        placeholder="e.g. Bar chart of likes for every model id.",
        height=110,
    )
    show_code = st.checkbox("Show the generated Python code", value=True)
    run_btn = st.button("Generate code and execute", type="primary")

    if not run_btn:
        return
    if not question.strip():
        st.error("Please type a question first.")
        return
    if not cfg.has_openai:
        st.error("OPENAI_API_KEY is missing. Set it in your .env file.")
        return

    with st.spinner("Writing Python for your question..."):
        t0 = time.time()
        try:
            generated = generate_python_code(question)
        except Exception as exc:
            st.error(f"Code generation failed: {exc}")
            return
        gen_seconds = time.time() - t0

    st.success(f"Code generated in {gen_seconds:.2f}s")
    if show_code:
        with st.expander("Generated Python", expanded=False):
            st.code(generated.code, language="python")

    sandbox = get_sandbox(sandbox_label)
    with st.spinner(f"Executing in: {sandbox_label}..."):
        result = sandbox.run(generated.code, cfg.database_url)

    cols = st.columns(3)
    cols[0].metric("Backend", result.backend)
    cols[1].metric("Status", "OK" if result.ok else "FAILED")
    cols[2].metric("Elapsed", f"{result.elapsed_seconds:.2f}s")
    if result.notes:
        st.caption(result.notes)

    if not result.ok:
        st.error("Sandbox execution failed.")
        with st.expander("Error details", expanded=True):
            st.code(result.stderr or "(no stderr)", language="bash")
        return

    parsed = parse_stdout(result.stdout)

    if parsed.no_data and not parsed.tables and not parsed.charts:
        st.info("The query returned no data.")
        return

    if parsed.text_answer:
        st.markdown("### Answer")
        st.write(parsed.text_answer)

    for i, df in enumerate(parsed.tables, start=1):
        st.markdown(f"### Table {i}")
        st.dataframe(df, use_container_width=True)

    for i, chart_json in enumerate(parsed.charts, start=1):
        st.markdown(f"### Chart {i}")
        try:
            fig = pio.from_json(json.dumps(chart_json))
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            st.warning(f"Could not render chart {i}: {exc}")
            with st.expander("Raw chart JSON"):
                st.json(chart_json)

    with st.expander("Raw stdout (debug)", expanded=False):
        st.code(result.stdout or "(empty)", language="text")
        if result.stderr:
            st.code(result.stderr, language="bash")


# ---------------------------------------------------------------------------
# Page: Top Models
# ---------------------------------------------------------------------------
def page_top_models() -> None:
    st.title("Top Models by Engagement")
    st.write(
        "Ranks tracked repositories by a composite engagement score that "
        "blends downloads, likes, and total discussions. Closure rate is "
        "shown alongside for triage context."
    )
    try:
        df = model_metrics.top_n_by_engagement(n=25)
    except Exception as exc:
        st.error(f"Could not query the database. {exc}")
        return
    if df.empty:
        st.info("No data yet. Run the ETL pipeline from the sidebar.")
        return
    st.dataframe(df, use_container_width=True)

    st.markdown("### Closure rate by repo")
    closure = sql_queries.closure_rate_by_repo()
    st.dataframe(closure, use_container_width=True)


# ---------------------------------------------------------------------------
# Page: Anomaly Detection
# ---------------------------------------------------------------------------
def page_anomaly_detection() -> None:
    st.title("Anomaly Detection")
    st.write(
        "Flags days where a model received an unusually large number of new "
        "discussions relative to its own 7 day rolling average. Threshold "
        "and minimum daily count are configurable below."
    )

    col1, col2, col3 = st.columns(3)
    window = col1.slider("Rolling window (days)", 3, 21, 7)
    multiplier = col2.slider("Spike multiplier", 1.5, 5.0, 2.0, step=0.5)
    min_daily = col3.slider("Minimum daily discussions", 1, 20, 3)

    try:
        spikes = anomaly_detection.detect_discussion_spikes(
            window=window, multiplier=multiplier, min_daily=min_daily
        )
    except Exception as exc:
        st.error(f"Could not query the database. {exc}")
        return

    if spikes.empty:
        st.success(
            "No spikes detected with the current thresholds. "
            "Either activity is steady or the thresholds are too strict."
        )
        return

    st.write(f"Detected **{len(spikes)}** spike days.")
    st.dataframe(spikes, use_container_width=True)


# ---------------------------------------------------------------------------
# Page: Forecasting
# ---------------------------------------------------------------------------
def page_forecasting() -> None:
    st.title("Forecasting")
    st.write(
        "Prophet projects created and closed discussion volume forward by "
        "14 days. Statsmodels Exponential Smoothing handles pull request "
        "style activity and a commit proxy series."
    )

    tabs = st.tabs(
        [
            "Created (Prophet)",
            "Closed (Prophet)",
            "Pull Requests (Statsmodels)",
            "Commits proxy (Statsmodels)",
        ]
    )

    with tabs[0]:
        fig = forecasting.prophet_forecast_created()
        if fig is None:
            st.info("Not enough data to fit Prophet on created discussions.")
        else:
            st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        fig = forecasting.prophet_forecast_closed()
        if fig is None:
            st.info("Not enough closed discussion data to fit Prophet.")
        else:
            st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        fig = forecasting.statsmodels_forecast_pull_requests()
        if fig is None:
            st.info("Not enough pull request style activity to fit a model.")
        else:
            st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        fig = forecasting.statsmodels_forecast_commits_proxy()
        if fig is None:
            st.info("Not enough activity history to fit a commit proxy model.")
        else:
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "The Hub API does not expose commit timelines uniformly, so "
                "total discussion activity is used as a stand in proxy. See "
                "Methodology for the full limitation."
            )


# ---------------------------------------------------------------------------
# Page: Data Quality
# ---------------------------------------------------------------------------
def page_data_quality() -> None:
    st.title("Data Quality")
    st.write(
        "Row level validation against the loaded tables. Use this page to "
        "confirm the dataset is trustworthy before reading the analysis."
    )
    try:
        df = data_quality.run_all_checks()
    except Exception as exc:
        st.error(f"Could not query the database. {exc}")
        return

    st.dataframe(df, use_container_width=True)

    failures = df[
        ~df["check_name"].isin(
            ["models.total_rows", "discussions.total_rows"]
        )
        & (df["offending_rows"] > 0)
    ]
    if failures.empty:
        st.success("All validation checks passed.")
    else:
        st.warning(f"{len(failures)} validation check(s) found issues.")
        st.dataframe(failures, use_container_width=True)


# ---------------------------------------------------------------------------
# Page: Methodology
# ---------------------------------------------------------------------------
def page_methodology() -> None:
    st.title("Methodology")
    methodology_path = (
        Path(__file__).resolve().parent.parent.parent / "doc" / "methodology.md"
    )
    limitations_path = (
        Path(__file__).resolve().parent.parent.parent / "doc" / "limitations.md"
    )
    if methodology_path.exists():
        st.markdown(methodology_path.read_text())
    else:
        st.info("Methodology document not found. See doc/methodology.md in the repo.")
    st.divider()
    st.subheader("Limitations")
    if limitations_path.exists():
        st.markdown(limitations_path.read_text())
    else:
        st.info("Limitations document not found. See doc/limitations.md in the repo.")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
PAGES = {
    "Executive Summary": page_executive_summary,
    "Agentic Analytics": page_agentic_analytics,
    "Top Models": page_top_models,
    "Anomaly Detection": page_anomaly_detection,
    "Forecasting": page_forecasting,
    "Data Quality": page_data_quality,
    "Methodology": page_methodology,
}

PAGES[page]()
