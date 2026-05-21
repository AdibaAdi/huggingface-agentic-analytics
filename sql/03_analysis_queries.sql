-- 03_analysis_queries.sql
-- Reproducible analysis queries. These match the helper functions in
-- src/analysis/sql_queries.py one for one, so the dashboard and the
-- written report cannot drift from each other.

-- 1. Which repo has the highest number of community discussions?
SELECT m.model_id,
       COUNT(d.id) AS discussion_count
FROM   model_repos m
JOIN   discussions d ON d.repo_id = m.id
GROUP  BY m.model_id
ORDER  BY discussion_count DESC;

-- 2. Total discussions per repo per weekday (Monday..Sunday).
SELECT m.model_id,
       TRIM(TO_CHAR(d.created_at, 'Day')) AS weekday,
       COUNT(*)                           AS discussion_count
FROM   model_repos m
JOIN   discussions d ON d.repo_id = m.id
WHERE  d.created_at IS NOT NULL
GROUP  BY m.model_id, TRIM(TO_CHAR(d.created_at, 'Day'))
ORDER  BY m.model_id;

-- 3. Day of the week with the most discussions created across all repos.
SELECT TRIM(TO_CHAR(d.created_at, 'Day')) AS weekday,
       COUNT(*)                           AS total_discussions
FROM   discussions d
WHERE  d.created_at IS NOT NULL
GROUP  BY TRIM(TO_CHAR(d.created_at, 'Day'))
ORDER  BY total_discussions DESC;

-- 4. Day of the week with the most discussions marked closed.
SELECT TRIM(TO_CHAR(d.closed_at, 'Day')) AS weekday,
       COUNT(*)                          AS closed_discussions
FROM   discussions d
WHERE  d.status = 'closed'
  AND  d.closed_at IS NOT NULL
GROUP  BY TRIM(TO_CHAR(d.closed_at, 'Day'))
ORDER  BY closed_discussions DESC;

-- 5. Closure rate by repo.
SELECT m.model_id,
       COUNT(d.id)                                                  AS total_discussions,
       SUM(CASE WHEN d.status = 'closed' THEN 1 ELSE 0 END)         AS closed_discussions,
       SUM(CASE WHEN d.status = 'open'   THEN 1 ELSE 0 END)         AS open_discussions,
       ROUND(
         SUM(CASE WHEN d.status = 'closed' THEN 1 ELSE 0 END)::numeric
         / NULLIF(COUNT(d.id), 0),
         2
       )                                                            AS closure_rate
FROM   model_repos m
LEFT   JOIN discussions d ON d.repo_id = m.id
GROUP  BY m.model_id
ORDER  BY closure_rate DESC NULLS LAST;

-- 6. Daily discussion volume across all repos for line charts.
SELECT DATE(d.created_at) AS day,
       COUNT(*)           AS total_discussions
FROM   discussions d
WHERE  d.created_at IS NOT NULL
GROUP  BY DATE(d.created_at)
ORDER  BY day;

-- 7. Discussions per model per day, used by the anomaly detector.
SELECT m.model_id,
       DATE(d.created_at) AS day,
       COUNT(*)           AS daily_discussions
FROM   model_repos m
JOIN   discussions d ON d.repo_id = m.id
WHERE  d.created_at IS NOT NULL
GROUP  BY m.model_id, DATE(d.created_at)
ORDER  BY m.model_id, day;

-- 8. Window function example: 7 day rolling average per model.
SELECT model_id,
       day,
       daily_discussions,
       AVG(daily_discussions) OVER (
         PARTITION BY model_id
         ORDER BY day
         ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
       ) AS rolling_7d_avg
FROM   (
    SELECT m.model_id,
           DATE(d.created_at) AS day,
           COUNT(*)           AS daily_discussions
    FROM   model_repos m
    JOIN   discussions d ON d.repo_id = m.id
    WHERE  d.created_at IS NOT NULL
    GROUP  BY m.model_id, DATE(d.created_at)
) daily
ORDER  BY model_id, day;
