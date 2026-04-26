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
st.caption("Bonus Assignment 1 + Bonus Assignment 2 starter app")

with st.sidebar:
    st.header("Setup / Status")
    st.write(f"Database URL set: {'Yes' if cfg.database_url else 'No'}")
    st.write(f"OPENAI_API_KEY set: {'Yes' if cfg.has_openai else 'No'}")
    st.write(f"HF_TOKEN set: {'Yes' if cfg.has_hf_token else 'No'}")
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
    "Create a table of total number of Discussions created for every repo for every day Monday-Sunday.",
    "Which day of the week has the highest number of total Discussions created across all tracked repos?",
    "Which day of the week has the highest number of total Discussions marked as Closed?",
]
st.write("Suggested queries:")
for e in examples:
    st.markdown(f"- {e}")

question = st.text_input("Natural language input", placeholder="Ask a question about the tracked Hugging Face repos...")

if st.button("Run Query"):
    route = route_question(question)
    text_answer, table_df = cached_query(route.action)

    st.markdown("### Text Answer")
    st.write(text_answer)
    st.caption(f"Router action: `{route.action}` — {route.reason}")

    st.markdown("### Table Output")
    if table_df.is_empty():
        st.info("No table data to display.")
    else:
        st.dataframe(table_df.to_pandas(), use_container_width=True)

st.markdown("---")
st.markdown("## Chart Output Section")

line_fig = charts.line_total_discussions_over_time()
pie_fig = charts.pie_discussions_distribution_by_model()
likes_fig = charts.bar_likes_per_model()
downloads_fig = charts.bar_downloads_per_model()
closed_week_fig = charts.bar_closed_discussions_per_week()
stacked_fig = charts.stacked_open_closed_per_model()

for fig in [line_fig, pie_fig, likes_fig, downloads_fig, closed_week_fig, stacked_fig]:
    if fig:
        st.plotly_chart(fig, use_container_width=True)

# Forecast charts (for selected model)
model_id = st.text_input("Model ID for forecast charts", value="")
if model_id:
    created_fc = charts.prophet_forecast_created_per_model(model_id)
    closed_fc = charts.prophet_forecast_closed_per_model(model_id)
    pr_fc, pr_note = charts.statsmodels_placeholder_forecast(model_id, metric="pull_requests")
    commit_fc, commit_note = charts.statsmodels_placeholder_forecast(model_id, metric="commits")

    st.markdown("### Prophet Forecasts")
    if created_fc:
        st.plotly_chart(created_fc, use_container_width=True)
    if closed_fc:
        st.plotly_chart(closed_fc, use_container_width=True)

    st.markdown("### Statsmodels Forecasts with Limitation/Fallback")
    st.info(pr_note)
    st.info(commit_note)
    if pr_fc:
        st.plotly_chart(pr_fc, use_container_width=True)
    if commit_fc:
        st.plotly_chart(commit_fc, use_container_width=True)

if not cfg.has_openai:
    st.warning("OPENAI_API_KEY missing. The app uses deterministic keyword routing fallback.")
