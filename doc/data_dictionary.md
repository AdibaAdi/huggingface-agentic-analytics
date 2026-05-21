# Data Dictionary

Field by field definitions for every table and view in the project.

## Table: `model_repos`

One row per Hugging Face model repository tracked by the pipeline.

| Column | Type | Description |
| --- | --- | --- |
| `id` | SERIAL PRIMARY KEY | Surrogate key. |
| `model_id` | VARCHAR(255), UNIQUE | Hugging Face repository identifier, for example `meta-llama/Llama-3.1-8B-Instruct`. |
| `tag` | VARCHAR(120) | Hugging Face category tag, for example `text-generation` or `summarization`. |
| `author` | VARCHAR(255) | Account or organization that owns the repository. |
| `likes` | INTEGER | Number of likes (used as a "stars" proxy). |
| `downloads` | INTEGER | Number of monthly downloads reported by the Hub (used as a "forks" or "usage" proxy). |
| `pipeline_tag` | VARCHAR(120) | The Hub's primary task pipeline tag for the repo. |
| `created_at` | TIMESTAMP | When the repository was created (nullable; some older repos have no creation date). |
| `last_modified` | TIMESTAMP | When the repository was last updated (nullable). |

## Table: `discussions`

One row per community discussion thread (issue or pull request) attached
to a tracked repository.

| Column | Type | Description |
| --- | --- | --- |
| `id` | SERIAL PRIMARY KEY | Surrogate key. |
| `repo_id` | INTEGER, FK | Foreign key to `model_repos.id`. |
| `hf_discussion_num` | INTEGER | The discussion number assigned by Hugging Face within the parent repo. |
| `title` | TEXT | Discussion title. |
| `author` | VARCHAR(255) | Account that opened the discussion. |
| `is_pull_request` | BOOLEAN | True when the discussion is a pull request. |
| `status` | VARCHAR(30) | Canonical value: `open` or `closed`. |
| `created_at` | TIMESTAMP | When the discussion was created. |
| `closed_at` | TIMESTAMP | When the discussion was closed (nullable). |

Uniqueness: `(repo_id, hf_discussion_num)` is unique.

## View: `v_discussions_clean`

Reusable cleaned view that joins each discussion to its parent repository
and adds derived columns.

| Column | Type | Description |
| --- | --- | --- |
| `id` | INTEGER | Discussion surrogate key. |
| `repo_id` | INTEGER | Parent repository surrogate key. |
| `model_id` | VARCHAR | Parent repository natural key (for example `meta-llama/Llama-3.1-8B-Instruct`). |
| `hf_discussion_num` | INTEGER | Discussion number within the parent repo. |
| `title` | TEXT | Discussion title. |
| `author` | VARCHAR | Discussion author. |
| `is_pull_request` | BOOLEAN | True when this thread is a pull request. |
| `status` | VARCHAR | Lowercased and trimmed status. |
| `is_closed` | BOOLEAN | Shortcut equal to `status = 'closed'`. |
| `created_at` | TIMESTAMP | When the discussion was created. |
| `closed_at` | TIMESTAMP | When the discussion was closed (nullable). |
| `weekday_created` | TEXT | Weekday name of `created_at` (`Monday`..`Sunday`). |
| `weekday_closed` | TEXT | Weekday name of `closed_at` if present. |

## View: `v_model_discussion_summary`

Per repository aggregate over the discussions table.

| Column | Type | Description |
| --- | --- | --- |
| `model_id` | VARCHAR | Repository natural key. |
| `tag` | VARCHAR | Hub category tag. |
| `likes` | INTEGER | Likes count for the repository. |
| `downloads` | INTEGER | Download count for the repository. |
| `total_discussions` | INTEGER | Total discussions on the repo. |
| `closed_discussions` | INTEGER | Discussions whose status is `closed`. |
| `open_discussions` | INTEGER | Discussions whose status is `open`. |
| `closure_rate` | NUMERIC(5,2) | `closed_discussions / total_discussions`, rounded to 2 decimals. |

## View: `v_discussions_by_weekday`

Discussion counts pivoted by weekday for fast charting.

| Column | Type | Description |
| --- | --- | --- |
| `model_id` | VARCHAR | Repository natural key. |
| `weekday` | TEXT | Weekday name (`Monday`..`Sunday`). |
| `discussion_count` | INTEGER | Number of discussions created on that weekday for that repo. |

## Derived metric: `engagement_score`

Computed in `src/analysis/model_metrics.py`. Formula:

```text
engagement_score = mean(
    normalize(downloads),
    normalize(likes),
    normalize(total_discussions)
)
```

Each input is min max normalized into `[0, 1]` across the tracked set, so
the score is bounded in `[0, 1]`. A constant input column normalizes to
zero. The score is an unweighted composite and is intended for ranking,
not for absolute comparison across runs.

## Derived metric: `closure_rate`

`closed_discussions / total_discussions` per repository. Returns null when
a repository has zero discussions. Capped between 0 and 1.

## Derived metric: `spike_ratio`

Computed in `src/analysis/anomaly_detection.py`. Formula:

```text
spike_ratio = daily_discussions / rolling_avg
rolling_avg = mean of last 7 daily_discussions for this model
```

A day is flagged as a spike when `spike_ratio` is at least the configured
multiplier (default 2.0) and `daily_discussions` is at least the minimum
floor (default 3). The detector is a baseline heuristic, not a hypothesis
test.
