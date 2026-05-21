-- 01_create_tables.sql
-- Schema for the Hugging Face Agentic Analytics project.
-- The SQLAlchemy ORM (src/db.py) creates these tables automatically on first run.
-- This file is provided so the schema can also be reviewed and applied with psql.

CREATE TABLE IF NOT EXISTS model_repos (
    id              SERIAL PRIMARY KEY,
    model_id        VARCHAR(255) NOT NULL UNIQUE,
    tag             VARCHAR(120) NOT NULL,
    author          VARCHAR(255),
    likes           INTEGER NOT NULL DEFAULT 0,
    downloads       INTEGER NOT NULL DEFAULT 0,
    pipeline_tag    VARCHAR(120),
    created_at      TIMESTAMP,
    last_modified   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_model_repos_tag ON model_repos (tag);

CREATE TABLE IF NOT EXISTS discussions (
    id                  SERIAL PRIMARY KEY,
    repo_id             INTEGER NOT NULL REFERENCES model_repos (id),
    hf_discussion_num   INTEGER NOT NULL,
    title               TEXT NOT NULL,
    author              VARCHAR(255),
    is_pull_request     BOOLEAN NOT NULL DEFAULT FALSE,
    status              VARCHAR(30) NOT NULL DEFAULT 'open',
    created_at          TIMESTAMP,
    closed_at           TIMESTAMP,
    CONSTRAINT uq_repo_discussion_num UNIQUE (repo_id, hf_discussion_num)
);

CREATE INDEX IF NOT EXISTS ix_discussions_repo_id ON discussions (repo_id);
CREATE INDEX IF NOT EXISTS ix_discussions_status ON discussions (status);
CREATE INDEX IF NOT EXISTS ix_discussions_created_at ON discussions (created_at);
