# Panopto Demo Script (5–10 minutes)

## 1) Intro (45 seconds)
- "This is `huggingface-agentic-analytics`, my class project for Bonus Assignment 1 and 2."
- "It pulls top Hugging Face models by tags, stores model + discussion data in PostgreSQL, and answers natural-language questions with text, tables, and charts in Streamlit."

## 2) Architecture walkthrough (90 seconds)
- Show root `README.md` architecture section.
- Mention stack: Streamlit, Polars, PostgreSQL/SQLAlchemy, Hugging Face Hub API, LangChain routing with GPT-4o-mini fallback logic, Prophet/Statsmodels forecasting.
- Mention safe code execution module (`src/code_executor.py`).

## 3) Environment setup (60 seconds)
- Show `.env.example` and explain required keys:
  - DATABASE_URL
  - OPENAI_API_KEY (optional but recommended)
  - HF_TOKEN (optional)
- Mention no real keys are committed.

## 4) Ingestion demo (90 seconds)
- Run `python src/ingest_hf_data.py`.
- Explain tags and top-5 selection per tag.
- Highlight fallback limitation for forks/commits/PR fields.

## 5) Streamlit app demo (2–3 minutes)
- Run `streamlit run src/app.py`.
- Show sidebar status and ingest button.
- Enter required natural-language queries and execute.
- Show text + table output.
- Scroll through required charts:
  - Total discussions over time
  - Discussion % by model
  - Likes/download bars
  - Closed/week, open vs closed stacked
  - Forecast charts (Prophet + Statsmodels fallback)

## 6) Bonus Assignment 2 demo (90 seconds)
- Open `src/bonus2_llamaindex_alternatives.py`.
- Explain four alternatives:
  1. LlamaIndex Code Interpreter tool path
  2. Docker sandbox
  3. OpenAI hosted code execution placeholder
  4. E2B cloud sandbox path
- Show comparative report and recommendation in `doc/comparative_analysis_report.md`.

## 7) Close (20 seconds)
- "This first version is intentionally simple, readable, and safe for class evaluation, with documented limitations and fallback behavior."
