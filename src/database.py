# Postgres persistence layer (Supabase).
# Called by run_digest.py and test_fetch.py.
#
#   create_tables()                  creates the jobs table if it doesn't exist (safe to call on every run)
#   insert_jobs(jobs)                upserts a list[Job], skips duplicates by url_hash → returns new row count
#   fetch_undigested_jobs()          returns all jobs not yet sent in a digest (digested_at IS NULL), newest first
#   mark_jobs_digested(url_hashes)   stamps digested_at=NOW() on the given rows after a successful digest send
#   save_ranking(result, all_jobs)   writes tier/tier_order/reason/ranked_at to the ranked rows; marks the rest 'skip'

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
    fetched_at    TIMESTAMPTZ NOT NULL,
    digested_at   TIMESTAMPTZ,
    tier          TEXT,
    tier_order    INTEGER,
    reason        TEXT,
    ranked_at     TIMESTAMPTZ
);
"""


def _connect():
    return psycopg2.connect(DATABASE_URL)


def create_tables() -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(CREATE_JOBS_TABLE)
    logger.info("Database tables ready")


def migrate_add_ranking_columns() -> None:
    """One-time migration: add ranking columns to existing jobs table."""
    stmts = [
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS tier       TEXT",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS tier_order INTEGER",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS reason     TEXT",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ranked_at  TIMESTAMPTZ",
    ]
    with _connect() as conn, conn.cursor() as cur:
        for stmt in stmts:
            cur.execute(stmt)
    logger.info("Ranking columns added to jobs table")


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


def fetch_undigested_jobs() -> list[Job]:
    """Return all jobs not yet sent in a digest (digested_at IS NULL), newest first."""
    sql = """
        SELECT url_hash, title, company, location, url, source, raw_snippet, description, fetched_at
        FROM jobs
        WHERE digested_at IS NULL
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

    logger.info(f"Fetched {len(jobs)} undigested jobs")
    return jobs


def fetch_jobs_by_ids(ids: list[int]) -> list[Job]:
    """Fetch specific jobs by their integer primary key."""
    if not ids:
        return []
    sql = """
        SELECT url_hash, title, company, location, url, source, raw_snippet, description, fetched_at
        FROM jobs
        WHERE id = ANY(%s)
        ORDER BY fetched_at DESC
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (ids,))
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

    logger.info(f"Fetched {len(jobs)} jobs by id")
    return jobs


def fetch_digested_jobs() -> list[Job]:
    """Return all jobs that have been sent in a digest, newest first."""
    sql = """
        SELECT url_hash, title, company, location, url, source, raw_snippet, description, fetched_at
        FROM jobs
        WHERE digested_at IS NOT NULL
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

    logger.info(f"Fetched {len(jobs)} digested jobs")
    return jobs


def mark_jobs_digested(url_hashes: list[str]) -> None:
    """Stamp digested_at=NOW() on the given jobs after a successful digest send."""
    if not url_hashes:
        return
    sql = """
        UPDATE jobs
        SET digested_at = NOW()
        WHERE url_hash = ANY(%s)
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (url_hashes,))
    logger.info(f"Marked {len(url_hashes)} jobs as digested")


def save_ranking(result, all_jobs: list[Job]) -> None:
    """Write ranking results back to the jobs rows.

    Ranked jobs (top / next_best) get tier, tier_order, reason, and ranked_at.
    Jobs that were evaluated but fell below the score threshold get tier='skip'.
    """
    now = datetime.now(timezone.utc)
    ranked_hashes: set[str] = set()
    rows = []

    for order, ranked_job in enumerate(result.top, start=1):
        rows.append((ranked_job.job.url_hash, 'top', order, ranked_job.reason, now))
        ranked_hashes.add(ranked_job.job.url_hash)

    for order, ranked_job in enumerate(result.next_best, start=1):
        rows.append((ranked_job.job.url_hash, 'next_best', order, ranked_job.reason, now))
        ranked_hashes.add(ranked_job.job.url_hash)

    skip_hashes = [job.url_hash for job in all_jobs if job.url_hash not in ranked_hashes]

    with _connect() as conn, conn.cursor() as cur:
        if rows:
            psycopg2.extras.execute_values(
                cur,
                """
                UPDATE jobs
                SET tier = data.tier, tier_order = data.tier_order,
                    reason = data.reason, ranked_at = data.ranked_at
                FROM (VALUES %s) AS data(url_hash, tier, tier_order, reason, ranked_at)
                WHERE jobs.url_hash = data.url_hash
                """,
                rows,
                template="(%s, %s, %s, %s, %s::timestamptz)",
            )
        if skip_hashes:
            cur.execute(
                "UPDATE jobs SET tier = 'skip', ranked_at = %s WHERE url_hash = ANY(%s)",
                (now, skip_hashes),
            )

    logger.info(f"Saved ranking: {len(result.top)} top, {len(result.next_best)} next_best, {len(skip_hashes)} skip")



