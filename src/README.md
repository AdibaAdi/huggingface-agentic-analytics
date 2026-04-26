# src/ Developer README

## Quick start
1. Create and activate your Python environment (Python 3.11 recommended).
2. Install dependencies:
   ```bash
   uv pip install -r src/requirements.txt
   ```
3. Configure `.env` at repository root.
4. Start PostgreSQL and ensure `DATABASE_URL` points to it.

## Commands
- Initialize DB + ingest HF data:
  ```bash
  python src/ingest_hf_data.py
  ```
- Run Streamlit:
  ```bash
  streamlit run src/app.py
  ```
- Run Bonus 2 sandbox alternatives demo:
  ```bash
  python -c "from src.bonus2_llamaindex_alternatives import demo_all_alternatives; print(demo_all_alternatives())"
  ```

## Notes
- Most transformations use Polars.
- Natural language query routing uses LangChain + GPT-4o-mini if API key exists.
- If API keys are missing, deterministic fallback behavior is used.
