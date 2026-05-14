import logging
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from config.config import DATABASE_URL
from src.gmail_fetcher import Job

logger = logging.getLogger(__name__)

CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id            SERIAL PRIMARY KEY,
    url_hash      TEXT UNIQUE NOT NULL,
    title         TEXT NOT NULL,
    company       TEXT,
    location      TEXT,
    url           TEXT NOT NULL,
    source        TEXT NOT NULL,
    raw_snippet   TEXT,
    description   TEXT,
    fetched_at    TIMESTAMPTZ NOT NULL
);
"""


def _connect():
    return psycopg2.connect(DATABASE_URL)


def create_tables() -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(CREATE_JOBS_TABLE)
    logger.info("Database tables ready")


def insert_jobs(jobs: list[Job]) -> int:
    """Insert jobs, skipping duplicates by url_hash. Returns count of new rows inserted."""
    if not jobs:
        return 0

    rows = [
        (
            job.url_hash,
            job.title,
            job.company,
            job.location,
            job.url,
            job.source,
            job.raw_snippet,
            job.description,
            job.fetched_at,
        )
        for job in jobs
    ]

    sql = """
        INSERT INTO jobs (url_hash, title, company, location, url, source, raw_snippet, description, fetched_at)
        VALUES %s
        ON CONFLICT (url_hash) DO NOTHING
    """

    with _connect() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)
        inserted = cur.rowcount

    logger.info(f"Inserted {inserted} new jobs ({len(jobs) - inserted} duplicates skipped)")
    return inserted
