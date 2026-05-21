# Limitations

Every dataset has things it cannot tell you. This document is an honest
list of what the Hugging Face Agentic Analytics dataset and analysis
cannot support, so reviewers can calibrate how much weight to put on any
single finding.

## 1. Source limitations

* **Downloads is a noisy popularity proxy.** Hugging Face download counts
  reflect API hits, not unique users or production traffic. Bots,
  automated re-downloads, and CI pipelines inflate the number.
* **Closed does not always mean resolved.** A discussion is marked closed
  in many cases that have nothing to do with resolution: the author
  closes it themselves, the maintainer triages without responding, or it
  is closed as a duplicate.
* **Discussion access is not uniform.** Some maintainers disable
  discussions entirely. Those repositories show up in the pipeline with
  zero discussion rows, and the comparative analysis silently understates
  their community activity.
* **Repository creation dates can be missing.** Older or migrated repos
  return a null `created_at`, which means any time series that filters on
  created date will exclude them.
* **The Hub API does not expose a uniform commit timeline.** Some
  repositories expose Git commit metadata; many do not. The commit
  forecast in the Forecasting page therefore uses total discussion
  activity as a stand in proxy. This is clearly labeled in the dashboard.

## 2. Scope limitations

* **Only the top 5 models per tag are tracked.** This is the assignment
  specification. A different ranking strategy or a larger sample would
  produce a different picture, especially of long tail repositories.
* **Only five Hub category tags are tracked.** Repositories tagged
  outside of `text-generation`, `image-text-to-text`,
  `text-classification`, `summarization`, and `automatic-speech-recognition`
  are not in the dataset.
* **The dataset is a snapshot.** Every metric reflects the moment the ETL
  pipeline last ran. Trend analyses assume the underlying repositories
  did not retroactively delete or modify discussions, which the Hub
  permits.

## 3. Analysis limitations

* **Engagement score is a heuristic.** Equal weighting of downloads,
  likes, and discussions is a deliberate, defensible choice, not an
  empirically validated weighting. It is suitable for ranking, not for
  precise cross dataset comparison.
* **Anomaly detection is a baseline.** It flags days that exceed a
  rolling average multiplier. It does not perform statistical testing,
  account for seasonality, or distinguish a spam wave from a genuine
  conversation surge.
* **Forecasts are exploratory.** Prophet and Statsmodels both fit
  reasonable defaults, but discussion volume is bursty and small. Do not
  use these forecasts for capacity planning.
* **Weekday aggregations reflect the Hub's timestamps**, which are in
  UTC. A discussion created at 02:00 UTC on a Tuesday is counted as
  Tuesday even if the author was in a timezone where it was still Monday.

## 4. Agentic system limitations

* **Generated code is non deterministic at temperature greater than zero.**
  The default temperature is zero, but it is still possible for the LLM
  to produce slightly different scripts on different runs.
* **The agent trusts the schema in the prompt.** If the schema in
  `src/app/code_generator.py` drifts from the actual database, the agent
  will produce code that errors. The unit tests do not cover this
  scenario.
* **Cloud sandboxes cannot reach local PostgreSQL.** The OpenAI Hosted
  and E2B backends operate on CSV exports of the tables. This is
  transparent to the generated code thanks to a shim, but it does mean
  the cloud backends see a snapshot rather than the live database.

## 5. Operational limitations

* **Hugging Face Hub rate limits.** Without an HF token, the API can
  rate limit large ingestions. The pipeline does not retry aggressively.
* **Prophet first run is slow.** Prophet compiles a Stan model on first
  use per Python environment. This is a one time cost, but it inflates
  cold start latency for the Forecasting page on a fresh machine.

Together these caveats mean the project is best read as a reproducible
case study and dashboard, not as a finished investigation. The findings
are honest, but every conclusion is conditional on the limitations above.
