# Comparative Analysis: LlamaIndex Code Execution Alternatives

**Assignment:** Bonus Assignment 2. Comparative analysis of four code
execution alternatives for a LlamaIndex agent that converts natural
language analytics prompts into executable Python over a Hugging Face and
PostgreSQL dataset.

## Test setup

* Dataset: top 5 Hugging Face models per tag across 5 tags (25 model
  repositories, approximately 1,300 community discussions) loaded into
  local PostgreSQL 16.
* Code generator: LlamaIndex `OpenAI(model="gpt-4o-mini")` with a strict
  schema aware system prompt (`src/app/code_generator.py`).
* Six representative prompts run end to end through every backend. Raw
  data lives in `comparative_analysis.json`, produced by
  `python -m src.app.run_comparative_analysis`.

## 1. Backend summary

| # | Alternative | Package or API | Network surface | Database access |
| --- | --- | --- | --- | --- |
| 1 | LlamaIndex Code Interpreter | `llama-index-tools-code-interpreter` | none (local subprocess) | direct to local PostgreSQL |
| 2 | Docker Python Sandbox | Docker CLI plus a custom `python:3.11-slim` image | container only | via `host.docker.internal` |
| 3 | OpenAI Hosted Code Execution | OpenAI Assistants API plus `code_interpreter` tool | OpenAI cloud | none. Data shipped as CSV. |
| 4 | E2B Cloud Sandbox | `e2b-code-interpreter` SDK | E2B cloud | none. Data shipped as CSV. |

## 2. Evaluation rubric

Each alternative is scored on six axes that matter for a production
analytics agent:

| Axis | What it measures |
| --- | --- |
| Security | Isolation from host filesystem and network. |
| Cold start latency | Time from `sandbox.run(...)` to first byte of stdout on a fresh process. |
| Steady state latency | Same call when the image or sandbox is warm. |
| Setup friction | What the developer must install or configure to use the backend. |
| Output fidelity | Whether the backend can return CSV tables AND Plotly chart JSON cleanly. |
| Cost | Per execution cost beyond the LLM call. |

## 3. Results

| Alternative | Security | Cold start | Steady state | Setup friction | Output fidelity | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| LlamaIndex CI | Low (host process) | about 0.5 s | about 0.3 s | None beyond pip install | Excellent (full stdout, all libraries) | 0 |
| Docker | High (container) | 30 to 60 s (first build) | 3 to 5 s | Docker Desktop required | Excellent | 0 |
| OpenAI Hosted | Very high (managed) | 10 to 25 s | 6 to 12 s | OpenAI account plus paid usage | Good (CSV upload required, no Postgres) | about 0.03 per call |
| E2B Cloud | Very high (managed) | 10 to 20 s | 5 to 10 s | E2B account plus paid usage | Good (CSV upload required, no Postgres) | about 0.01 to 0.02 per call |

Latency numbers are from a 16 GB M series MacBook running PostgreSQL 16
locally. They are illustrative, not formal benchmarks. Reproduce them via
`python -m src.app.run_comparative_analysis`.

### 3.1 Output fidelity details

All four backends successfully returned the marker delimited stdout
produced by the generated code:

```text
<<<TABLE_START>>> ... CSV ... <<<TABLE_END>>>
<<<CHART_START>>> ... Plotly JSON ... <<<CHART_END>>>
```

The two managed cloud backends require a small CSV mode shim because they
cannot reach a developer's local PostgreSQL. The shim transparently
replaces `pl.read_database` with a join over the uploaded CSVs, so the
LLM generated code runs unmodified.

### 3.2 Failure modes observed

| Backend | Typical failures | How we handle them |
| --- | --- | --- |
| LlamaIndex CI | Host package missing (for example `prophet` not installed) | Bubble up stderr, instruct user to `uv pip install`. |
| Docker | Image build failed, daemon not running | Clear error message in the UI, suggest Docker Desktop. |
| OpenAI Hosted | Run timeout on long tail CSV uploads | 180 second polling cap, return `last_error`. |
| E2B | Quota exhausted, wrong API key | Clear message, fall back instructions. |

## 4. Recommendations by use case

* **Classroom demo and live grading session:** LlamaIndex Code Interpreter.
  Zero setup beyond `pip install`, fastest iteration, easiest to reason
  about when something fails.
* **Local development with stronger isolation:** Docker. Once the image
  is cached the latency is acceptable, and you get a hard sandbox
  boundary without paying per execution.
* **Multi tenant SaaS where untrusted users submit prompts:** E2B or
  OpenAI Hosted. Both fully managed, both isolate execution from your
  infrastructure. E2B is cheaper and gives more control over the runtime;
  OpenAI's hosted CI is simpler to wire up but locks you into the
  Assistants API shape.
* **Production agent talking to a private database:** Docker or a self
  hosted E2B template. The two cloud backends cannot reach private
  PostgreSQL directly, so you either ship CSVs (the current approach) or
  stand up a read only API in front of the database.

## 5. Concrete observations from this assignment

1. **Code generation is the bottleneck, not execution.** GPT 4o mini
   averaged 1.2 to 2.5 seconds per prompt to produce the script. Sandbox
   execution on every backend except cold Docker took less than that.
2. **Forecast prompts revealed a real fidelity gap.** On LlamaIndex CI
   and Docker the figures rendered immediately. On the cloud backends the
   CSV shim worked, but Prophet's first run Stan compilation added about
   30 seconds on top of cloud start up, making them less suitable for
   interactive forecasting.
3. **The marker based stdout protocol is robust across backends.** The
   parser does not depend on file artifacts coming back from the sandbox,
   so the exact same parser handles all four backends. This is a
   deliberate design choice that pays off when swapping execution layers.
4. **Schema in prompt beats schema discovery.** Putting the explicit
   PostgreSQL schema into the system prompt produced cleaner SQL than
   letting the LLM query `information_schema`, and reduced wasted tokens.

## 6. Conclusion

For this assignment the best practical default is the LlamaIndex Code
Interpreter for development and Docker for grading or demo with stronger
isolation. The two managed cloud backends are valuable in production
contexts where you cannot trust the user prompt, but for a single
developer analytics workflow over a local database they introduce more
friction than they remove. The architecture intentionally treats the four
backends as hot swappable, so a future migration to E2B or OpenAI Hosted
requires no changes to the agent or the UI, only flipping the dropdown in
the sidebar.

See `comparative_analysis.json` for the raw run data backing this report.
