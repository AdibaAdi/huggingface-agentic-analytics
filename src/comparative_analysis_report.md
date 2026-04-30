# Comparative Analysis: LlamaIndex Code Execution Alternatives

**Assignment:** Bonus #2 — comparative analysis of 4 code-execution alternatives
for a LlamaIndex agent that converts natural-language analytics prompts into
executable Python over a Hugging Face / Postgres dataset.

**Test setup**
- Dataset: top-5 Hugging Face models per tag across 5 tags (25 model repos,
  ~1,300 community discussions) loaded into local Postgres 14.
- Code generator: LlamaIndex `OpenAI(model="gpt-4o-mini")` with a strict
  schema-aware system prompt.
- Six representative prompts run end-to-end through every backend (see
  `comparative_analysis.json` for raw data).

---

## 1. Backend summary

| # | Alternative | Package / API | Network | Has DB access |
|---|---|---|---|---|
| 1 | LlamaIndex Code Interpreter | `llama-index-tools-code-interpreter` | none (local subprocess) | ✅ direct to local Postgres |
| 2 | Docker Python Sandbox | Docker CLI + custom `python:3.11-slim` image | container only | ✅ via `host.docker.internal` |
| 3 | OpenAI Hosted Code Execution | OpenAI Assistants API + `code_interpreter` tool | OpenAI cloud | ❌ — data shipped as CSV |
| 4 | E2B Cloud Sandbox | `e2b-code-interpreter` SDK | E2B cloud | ❌ — data shipped as CSV |

---

## 2. Evaluation rubric

We score each alternative on six axes that matter for a production analytics
agent:

| Axis | What it measures |
|---|---|
| **Security** | Isolation from host filesystem / network |
| **Cold-start latency** | Time from `sandbox.run(...)` to first byte of stdout on a fresh process |
| **Steady-state latency** | Same call when image / sandbox warm |
| **Setup friction** | What the developer must install/configure |
| **Output fidelity** | Can it return CSV tables AND Plotly chart JSON cleanly? |
| **Cost** | Per-execution cost beyond the LLM call |

---

## 3. Results

| Alternative | Security | Cold start | Steady state | Setup friction | Output fidelity | Cost |
|---|---|---|---|---|---|---|
| LlamaIndex CI | Low (host process) | ~0.5 s | ~0.3 s | None — pip install only | Excellent (full stdout, all libs) | $0 |
| Docker | High (container) | ~30–60 s (first build) | ~3–5 s | Docker Desktop required | Excellent | $0 |
| OpenAI Hosted | Very high (managed) | ~10–25 s | ~6–12 s | OpenAI account + paid usage | Good (CSV upload required, no Postgres) | ~$0.03 / call |
| E2B Cloud | Very high (managed) | ~10–20 s | ~5–10 s | E2B account + paid usage | Good (CSV upload required, no Postgres) | ~$0.01–0.02 / call |

(Latency numbers are from a 16 GB M-series MacBook running Postgres 14 locally;
they are illustrative, not benchmarks. Reproduce via
`run_comparative_analysis.py` on your machine.)

### 3.1 Output fidelity details

All four backends successfully returned the marker-delimited stdout produced
by the LLM:

```
<<<TABLE_START>>> ... CSV ... <<<TABLE_END>>>
<<<CHART_START>>> ... plotly JSON ... <<<CHART_END>>>
```

The two managed cloud backends required a small CSV-mode shim because they
cannot reach a developer's local Postgres. The shim transparently swaps
`pl.read_database` for a join over the uploaded CSVs, so the LLM-generated
code runs unmodified.

### 3.2 Failure modes observed

| Backend | Typical failures | How we handle them |
|---|---|---|
| LlamaIndex CI | host package missing (e.g. `prophet` not installed) | bubble up stderr, instruct user to `uv pip install` |
| Docker | image build failed, daemon not running | clear error message in UI, suggest Docker Desktop |
| OpenAI Hosted | run timeout on long-tail CSV uploads | 180 s polling cap, return `last_error` |
| E2B | quota exhausted, wrong API key | clear message, fall back instructions |

---

## 4. Recommendations by use case

- **Classroom demo / live grading session** → **LlamaIndex CI**. Zero setup
  beyond `pip install`, fastest iteration, easiest to reason about when
  something fails.
- **Local development with stronger isolation** → **Docker**. Once the image
  is cached the latency is acceptable, and you get a hard sandbox boundary
  without paying per execution.
- **Multi-tenant SaaS where untrusted users submit prompts** → **E2B** or
  **OpenAI Hosted**. Both fully managed, both isolate execution from your
  infra. E2B is cheaper and gives more control over the runtime; OpenAI's
  hosted CI is simpler to wire up but locks you into the Assistants API
  shape.
- **Production agent talking to a private database** → **Docker** or a
  self-hosted E2B template. The two cloud backends cannot reach private
  Postgres directly, so you either ship CSVs (current approach) or stand up
  a read-only API in front of the DB.

---

## 5. Concrete observations from this assignment

1. **Code generation is the bottleneck**, not execution. GPT-4o-mini
   averaged ~1.2–2.5 s per prompt to produce the script; sandbox execution
   on every backend except cold-Docker took less than that.
2. **Forecast prompts (Prophet/Statsmodels) revealed a real fidelity gap.**
   On LlamaIndex CI and Docker the figures rendered immediately. On the
   cloud backends the CSV shim worked, but Prophet's first-run Stan
   compilation added ~30 s on top of cloud start-up — making them less
   suitable for interactive forecasting.
3. **The marker-based stdout protocol is robust across backends.** Because
   we never depend on file artifacts coming back from the sandbox, the
   exact same parser handles all four backends. This is a deliberate design
   choice that pays off when swapping execution layers.
4. **Schema-in-prompt > schema-discovery.** Putting the explicit Postgres
   schema into the system prompt produced cleaner SQL than letting the LLM
   query `information_schema`, and reduced wasted tokens.

---

## 6. Conclusion

For this assignment the best practical default is **LlamaIndex Code
Interpreter** for development and **Docker** for grading/demo with stronger
isolation. The two managed cloud backends are valuable in production
contexts where you can't trust the user's prompt, but for a single-developer
analytics workflow over a local database they introduce more friction than
they remove. The architecture intentionally treats the four backends as
hot-swappable, so a future migration to E2B or OpenAI Hosted requires no
changes to the agent or the UI — only flipping the dropdown in the sidebar.

See `comparative_analysis.json` for the raw run data backing this report.
