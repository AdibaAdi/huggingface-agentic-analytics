-- 02_cleaning_views.sql
-- Reusable cleaning views that normalize timestamps, weekdays, and status
-- values so downstream analysis queries do not have to repeat the same
-- expressions. Re-running this file is safe; views are dropped and recreated.

DROP VIEW IF EXISTS v_discussions_clean CASCADE;
DROP VIEW IF EXISTS v_model_discussion_summary CASCADE;
DROP VIEW IF EXISTS v_discussions_by_weekday CASCADE;

-- Canonical discussions view.
-- Adds derived columns used everywhere else:
--   weekday_created : weekday name (Monday..Sunday) of created_at
--   weekday_closed  : weekday name of closed_at, if present
--   is_closed       : boolean shortcut on status
CREATE VIEW v_discussions_clean AS
SELECT d.id,
       d.repo_id,
       m.model_id,
       d.hf_discussion_num,
       d.title,
       d.author,
       d.is_pull_request,
       LOWER(TRIM(d.status))                                AS status,
       (LOWER(TRIM(d.status)) = 'closed')                   AS is_closed,
       d.created_at,
       d.closed_at,
       TRIM(TO_CHAR(d.created_at, 'Day'))                   AS weekday_created,
       CASE
         WHEN d.closed_at IS NOT NULL
           THEN TRIM(TO_CHAR(d.closed_at, 'Day'))
         ELSE NULL
       END                                                  AS weekday_closed
FROM   discussions d
JOIN   model_repos m ON m.id = d.repo_id;

-- Per repo summary of discussion volume and closure rate.
CREATE VIEW v_model_discussion_summary AS
SELECT m.model_id,
       m.tag,
       m.likes,
       m.downloads,
       COUNT(d.id)                                                       AS total_discussions,
       SUM(CASE WHEN d.status = 'closed' THEN 1 ELSE 0 END)              AS closed_discussions,
       SUM(CASE WHEN d.status = 'open'   THEN 1 ELSE 0 END)              AS open_discussions,
       ROUND(
         SUM(CASE WHEN d.status = 'closed' THEN 1 ELSE 0 END)::numeric
         / NULLIF(COUNT(d.id), 0),
         2
       )                                                                 AS closure_rate
FROM   model_repos m
LEFT   JOIN discussions d ON d.repo_id = m.id
GROUP  BY m.model_id, m.tag, m.likes, m.downloads;

-- Discussion counts pivoted by weekday for fast charting.
CREATE VIEW v_discussions_by_weekday AS
SELECT model_id,
       weekday_created                AS weekday,
       COUNT(*)                       AS discussion_count
FROM   v_discussions_clean
WHERE  created_at IS NOT NULL
GROUP  BY model_id, weekday_created;
