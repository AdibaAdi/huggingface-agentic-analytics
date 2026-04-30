"""Hugging Face Agentic Analytics -- Streamlit UI (Bonus 2 compliant).

Flow per user prompt:
  1. User types a natural-language question in a free text box.
  2. LlamaIndex + GPT-4o-mini generates a self-contained Python script.
  3. User picks ONE of 4 sandboxes from the dropdown:
       - LlamaIndex Code Interpreter  (CodeInterpreterToolSpec)
       - Docker Python Sandbox        (python:3.11-slim container)
       - OpenAI Hosted Code Execution (Assistants API + Code Interpreter)
       - E2B Cloud Sandbox            (e2b-code-interpreter)
  4. The chosen sandbox executes the generated code.
  5. We parse stdout for CSV tables and Plotly chart JSON, then render.

There are NO hardcoded SQL queries, NO hardcoded Polars pipelines, and NO
action-router enums. Every result -- text, table, chart -- comes from code
that the LLM wrote at runtime in response to the user's prompt.
"""

from __future__ import annotations

import json
import time

import plotly.io as pio
import streamlit as st

from code_generator import generate_python_code
from config import get_config
from ingest_hf_data import ingest_data
from output_parser import parse_stdout
from sandboxes import SANDBOXES, get_sandbox

st.set_page_config(page_title="Hugging Face Agentic Analytics", layout="wide")
cfg = get_config()

st.title("🤗 Hugging Face Agentic Analytics")
st.caption(
    "LlamaIndex agent → LLM-generated Python → execute in your chosen sandbox "
    "(LlamaIndex CI / Docker / OpenAI Hosted / E2B)"
)

# ----------------------------- Sidebar -------------------------------
with st.sidebar:
    st.header("Setup / Status")
    st.write(f"DATABASE_URL set: {'✅' if cfg.database_url else '❌'}")
    st.write(f"OPENAI_API_KEY: {'✅' if cfg.has_openai else '❌'}")
    st.write(f"HUGGINGFACE_API_TOKEN: {'✅' if cfg.has_hf_token else '❌'}")
    st.write(f"E2B_API_KEY: {'✅' if cfg.has_e2b else '❌'}")
    st.write("**Tracked tags:**")
    st.code("\n".join(cfg.hf_tags))

    if st.button("Ingest / Refresh HF Data"):
        with st.spinner("Pulling top 5 models per tag + their discussions..."):
            try:
                summary = ingest_data()
                st.success("Ingestion completed")
                st.json(summary)
            except Exception as exc:
                st.error(f"Ingestion failed: {exc}")

    st.markdown("---")
    st.markdown("**Bonus 2 sandbox selector**")
    sandbox_label = st.selectbox(
        "Code execution backend",
        list(SANDBOXES.keys()),
        index=0,
        help="Choose which of the 4 alternatives executes the LLM-generated code.",
    )

# ----------------------------- Main UI -------------------------------
st.subheader("Ask any natural-language analytics question")

with st.expander("Example prompts (click to expand)", expanded=False):
    st.markdown(
        """
**Text / table queries:**
- Which Hugging Face model repo has the highest number of Community Discussions created?
- Create a table of the total number of Discussions created for every repo for every day of the week (Monday-Sunday).
- Which day of the week has the highest number of total Discussions created across all tracked Hugging Face repos?
- Which day of the week has the highest number of total Discussions marked as 'Closed' for all Hugging Face repos?

**Chart queries:**
- Line chart: total Discussions over time across all models.
- Pie chart: % distribution of total Discussions belonging to each model.
- Bar chart: Likes count for every Model ID.
- Bar chart: Downloads for every Model ID (used as 'forks' proxy).
- Bar chart: closed Discussions per week.
- Stacked bar chart: open vs closed Discussions for every Model.
- Use Prophet to forecast created Discussions for every Model.
- Use Prophet to forecast closed Discussions for every Model.
- Use Statsmodels to forecast Pull Requests for every Model.
- Use Statsmodels to forecast Commits for every Model.
        """
    )

question = st.text_area(
    "Your prompt",
    placeholder="e.g. Show me a bar chart of likes for every model id.",
    height=100,
)

show_code = st.checkbox("Show generated Python code", value=True)
run_btn = st.button("🚀 Generate code and execute", type="primary")

# ----------------------------- Execution -------------------------------
if run_btn:
    if not question.strip():
        st.error("Please type a natural-language question before running.")
        st.stop()
    if not cfg.has_openai:
        st.error("OPENAI_API_KEY is missing. Set it in your .env file.")
        st.stop()

    # 1. Generate Python via LlamaIndex agent
    with st.spinner("🧠 LLM is writing Python code for your question..."):
        t0 = time.time()
        try:
            generated = generate_python_code(question)
        except Exception as exc:
            st.error(f"Code generation failed: {exc}")
            st.stop()
        gen_seconds = time.time() - t0

    st.success(f"Code generated in {gen_seconds:.2f}s")
    if show_code:
        with st.expander("📜 Generated Python code", expanded=False):
            st.code(generated.code, language="python")

    # 2. Execute in chosen sandbox
    sandbox = get_sandbox(sandbox_label)
    with st.spinner(f"⚙️ Executing in: {sandbox_label} ..."):
        result = sandbox.run(generated.code, cfg.database_url)

    # 3. Render execution metadata
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
        st.stop()

    # 4. Parse output
    parsed = parse_stdout(result.stdout)

    if parsed.no_data and not parsed.tables and not parsed.charts:
        st.info("The query returned no data.")
        st.stop()

    if parsed.text_answer:
        st.markdown("### 📝 Answer")
        st.write(parsed.text_answer)

    for i, df in enumerate(parsed.tables, start=1):
        st.markdown(f"### 📊 Table {i}")
        st.dataframe(df, use_container_width=True)

    for i, chart_json in enumerate(parsed.charts, start=1):
        st.markdown(f"### 📈 Chart {i}")
        try:
            fig = pio.from_json(json.dumps(chart_json))
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            st.warning(f"Could not render chart {i}: {exc}")
            with st.expander("Raw chart JSON"):
                st.json(chart_json)

    with st.expander("🔍 Raw stdout (debug)", expanded=False):
        st.code(result.stdout or "(empty)", language="text")
        if result.stderr:
            st.code(result.stderr, language="bash")
