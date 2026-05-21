# Executive Summary

This summary distills the headline findings from the Hugging Face Agentic
Analytics project for a non technical reader. Numbers in the dashboard
update automatically when the underlying database is re-ingested; the
findings below describe the patterns that have held across multiple runs.

## What the project is

A reproducible Python data pipeline and dashboard that collects model and
discussion metadata from the public Hugging Face Hub API, cleans it,
stores it in PostgreSQL, and lets an analyst ask natural language
questions answered with tables and charts.

## Key findings

1. **Community activity is concentrated in a small number of repositories.**
   The top three or four repositories by total discussions consistently
   account for the majority of community conversation across the tracked
   set. The long tail is much quieter.
2. **Popularity does not equal community traffic.** Downloads and total
   discussions are only loosely correlated. Some heavily downloaded
   repositories have very few open discussion threads, and some smaller
   repositories generate disproportionate community traffic.
3. **New discussions cluster on weekdays.** Across the tracked set, new
   discussion creation peaks in the middle of the work week and drops
   sharply on weekends.
4. **Closures lag creations.** Discussion closures also cluster on
   weekdays, but typically peak a day or two after the creation peak,
   suggesting maintainers triage in batches rather than continuously.
5. **Closure rates vary widely.** Some repositories close a high
   percentage of their discussions; others leave most open. Closure rate
   is one of the clearer signals of active maintenance.
6. **Spike days are rare but real.** The rolling baseline anomaly
   detector typically flags a handful of days where a single repository
   received four to five times its normal discussion volume. These
   spikes coincide with major releases or external news, not with random
   noise.

## How to read the dashboard

* Start on the **Executive Summary** page for the headline numbers.
* Use the **Agentic Analytics** page to ask any natural language
  question.
* Visit **Top Models** for a ranked engagement table.
* Use **Anomaly Detection** to surface unusual activity days.
* Use **Forecasting** for Prophet and Statsmodels projections.
* Check **Data Quality** before drawing conclusions; the checks show how
  trustworthy the underlying dataset is.

## What this project cannot tell you

The findings above are conditional on the limitations listed in
`limitations.md`. The most important caveats:

* Hugging Face download counts are a noisy popularity signal.
* Closed discussions are not necessarily resolved discussions.
* Some maintainers disable community discussions entirely, which
  artificially understates their repos.
* The dataset is a snapshot, not a live feed.

For technical details on how the numbers are computed, see
`doc/methodology.md` and `doc/data_dictionary.md`.
