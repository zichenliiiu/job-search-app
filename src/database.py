# Postgres persistence layer (Supabase).
# Called by run_digest.py and test_fetch.py.
#
#   create_tables()               creates the jobs table if it doesn't exist (safe to call on every run)
#   insert_jobs(jobs)             upserts a list[Job], skips duplicates by url_hash → returns new row count
#   fetch_recent_jobs(hours=24)   returns jobs fetched within the last N hours, newest first
#   fetch_all_jobs()              returns all jobs in the database, newest first

import logging
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from config.config import DATABASE_URL
from src.job_class import Job

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


def fetch_recent_jobs(hours: int = 24) -> list[Job]:
    """Return jobs fetched within the last N hours, newest first."""
    sql = """
        SELECT url_hash, title, company, location, url, source, raw_snippet, description, fetched_at
        FROM jobs
        WHERE fetched_at >= NOW() - INTERVAL '%s hours'
        ORDER BY fetched_at DESC
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (hours,))
        rows = cur.fetchall()

    jobs = []
    for row in rows:
        url_hash, title, company, location, url, source, raw_snippet, description, fetched_at = row
        job = Job(
            title=title or '',
            company=company or '',
            location=location or '',
            url=url,
            source=source,
            raw_snippet=raw_snippet or '',
            description=description or '',
            fetched_at=fetched_at,
        )
        jobs.append(job)

    logger.info(f"Fetched {len(jobs)} jobs from last {hours}h")
    return jobs


def fetch_all_jobs() -> list[Job]:
    """Return all jobs from the database, newest first."""
    sql = """
        SELECT url_hash, title, company, location, url, source, raw_snippet, description, fetched_at
        FROM jobs
        ORDER BY fetched_at DESC
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    jobs = []
    for row in rows:
        url_hash, title, company, location, url, source, raw_snippet, description, fetched_at = row
        job = Job(
            title=title or '',
            company=company or '',
            location=location or '',
            url=url,
            source=source,
            raw_snippet=raw_snippet or '',
            description=description or '',
            fetched_at=fetched_at,
        )
        jobs.append(job)

    logger.info(f"Fetched {len(jobs)} jobs from database")
    return jobs
