"""Streamlit UI for Hugging Face agentic analytics."""

from __future__ import annotations

import streamlit as st

import charts
from analytics_queries import resolve_action
from config import get_config
from ingest_hf_data import ingest_data
from langchain_agent import route_question

st.set_page_config(page_title="Hugging Face Agentic Analytics", layout="wide")

cfg = get_config()


@st.cache_data(ttl=60)
def cached_query(action: str):
    return resolve_action(action)


st.title("Hugging Face Agentic Analytics")
st.caption("Natural language -> LLM router -> deterministic analytics action")

with st.sidebar:
    st.header("Setup / Status")
    st.write(f"Database URL set: {'Yes' if cfg.database_url else 'No'}")
    st.write(f"OPENAI_API_KEY set: {'Yes' if cfg.has_openai else 'No'}")
    st.write(f"HUGGINGFACE_API_TOKEN set: {'Yes' if cfg.has_hf_token else 'No'}")
    st.write("Tracked tags:")
    st.code("\n".join(cfg.hf_tags))

    if st.button("Ingest / Refresh Hugging Face Data"):
        with st.spinner("Ingesting... this can take up to a minute"):
            try:
                summary = ingest_data()
                st.success("Ingestion completed")
                st.json(summary)
                cached_query.clear()
            except Exception as exc:
                st.error(f"Ingestion failed: {exc}")

st.subheader("Ask a natural language question")
examples = [
    "Which Hugging Face model repo has the highest number of Community Discussions created?",
    "Create a table of total discussions created for every repo for every day Monday-Sunday.",
    "Show a chart of closed discussions per week.",
    "Forecast pull requests for model gpt2.",
]
st.write("Example prompts (suggestions only):")
for e in examples:
    st.markdown(f"- {e}")

question = st.text_input("Natural language prompt", placeholder="Type your own question...")
model_id = st.text_input("Model ID (only needed for forecast actions)", value="")

if st.button("Run Query"):
    if not question.strip():
        st.error("Please enter a natural language prompt before running the query.")
        st.stop()

    route = route_question(question)
    st.caption(f"LLM selected action: `{route.action}`")
    st.caption(f"Reason: {route.reason}")

    if route.action == "error":
        st.error(route.reason)
        st.stop()

    text_actions = {
        "highest_discussions",
        "table_discussions_weekday",
        "day_most_created",
        "day_most_closed",
    }
    chart_actions = {
        "chart_total_discussions_over_time",
        "chart_discussions_distribution_by_model",
        "chart_likes_per_model",
        "chart_downloads_per_model",
        "chart_closed_discussions_per_week",
        "chart_open_closed_per_model",
        "forecast_created_discussions",
        "forecast_closed_discussions",
        "forecast_pull_requests",
        "forecast_commits",
    }
    result_rendered = False

    if route.action in text_actions:
        text_answer, table_df = cached_query(route.action)
        st.markdown("### Text Answer")
        st.write(text_answer)

        st.markdown("### Table Output")
        if table_df.is_empty():
            st.info("No table data to display.")
        else:
            st.dataframe(table_df.to_pandas(), use_container_width=True)
        result_rendered = True

    elif route.action in chart_actions:
        chart_mapping = {
            "chart_total_discussions_over_time": charts.line_total_discussions_over_time,
            "chart_discussions_distribution_by_model": charts.pie_discussions_distribution_by_model,
            "chart_likes_per_model": charts.bar_likes_per_model,
            "chart_downloads_per_model": charts.bar_downloads_per_model,
            "chart_closed_discussions_per_week": charts.bar_closed_discussions_per_week,
            "chart_open_closed_per_model": charts.stacked_open_closed_per_model,
        }
        if route.action in {
            "forecast_created_discussions",
            "forecast_closed_discussions",
            "forecast_pull_requests",
            "forecast_commits",
        } and not model_id.strip():
            st.error(
                "This forecast action requires a Model ID. Please enter a model ID in the sidebar field and run again."
            )
            st.stop()

        if route.action == "forecast_created_discussions":
            fig = charts.prophet_forecast_created_per_model(model_id)
            st.info("Prophet forecast for created discussions.")
        elif route.action == "forecast_closed_discussions":
            fig = charts.prophet_forecast_closed_per_model(model_id)
            st.info("Prophet forecast for closed discussions.")
        elif route.action == "forecast_pull_requests":
            fig, note = charts.statsmodels_placeholder_forecast(model_id, metric="pull_requests")
            st.info(note)
        elif route.action == "forecast_commits":
            fig, note = charts.statsmodels_placeholder_forecast(model_id, metric="commits")
            st.info(note)
        else:
            result = chart_mapping[route.action]()
            if isinstance(result, tuple):
                fig, message = result
                if message:
                    st.info(message)
            else:
                fig = result

        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Not enough data available to generate this chart.")
        result_rendered = True

    else:
        st.error("Unsupported action selected by router.")

    if result_rendered:
        st.caption("This result was generated through LLM-based routing and database-backed analytics.")
