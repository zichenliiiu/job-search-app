from __future__ import annotations

# Postgres persistence layer (Supabase).
# Called by fetch_jobs.py, send_digest.py, and test_fetch.py.
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

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    provider      TEXT NOT NULL,
    provider_sub  TEXT NOT NULL,
    email         TEXT NOT NULL,
    name          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, provider_sub)
);
"""

CREATE_USER_CRITERIA_TABLE = """
CREATE TABLE IF NOT EXISTS user_criteria (
    user_id       INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    criteria_text TEXT NOT NULL DEFAULT ''
);
"""

CREATE_USER_COMPANIES_TABLE = """
CREATE TABLE IF NOT EXISTS user_companies (
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company       TEXT NOT NULL,
    PRIMARY KEY (user_id, company)
);
"""


def _connect():
    return psycopg2.connect(DATABASE_URL)


def create_tables() -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(CREATE_JOBS_TABLE)
        cur.execute(CREATE_USERS_TABLE)
        cur.execute(CREATE_USER_CRITERIA_TABLE)
        cur.execute(CREATE_USER_COMPANIES_TABLE)
    logger.info("Database tables ready")


def get_or_create_user(provider: str, provider_sub: str, email: str, name: str) -> dict:
    """Look up a user by (provider, provider_sub), creating one if it doesn't exist.

    Returns a dict with id, provider, provider_sub, email, name.
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, provider, provider_sub, email, name FROM users WHERE provider = %s AND provider_sub = %s",
            (provider, provider_sub),
        )
        row = cur.fetchone()
        if row is None:
            cur.execute(
                """
                INSERT INTO users (provider, provider_sub, email, name)
                VALUES (%s, %s, %s, %s)
                RETURNING id, provider, provider_sub, email, name
                """,
                (provider, provider_sub, email, name),
            )
            row = cur.fetchone()
            logger.info(f"Created new user: {email} ({provider})")

    return {"id": row[0], "provider": row[1], "provider_sub": row[2], "email": row[3], "name": row[4]}


def get_user_by_id(user_id: int) -> dict | None:
    """Look up a user by their internal id. Returns None if not found."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, provider, provider_sub, email, name FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()

    if row is None:
        return None
    return {"id": row[0], "provider": row[1], "provider_sub": row[2], "email": row[3], "name": row[4]}


def get_user_criteria(user_id: int) -> dict:
    """Return {criteria_text} for the user, defaulting to an empty string."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT criteria_text FROM user_criteria WHERE user_id = %s", (user_id,))
        row = cur.fetchone()

    if row is None:
        return {"criteria_text": ""}
    return {"criteria_text": row[0]}


def save_user_criteria(user_id: int, criteria_text: str) -> None:
    """Upsert the user's ranking criteria text."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_criteria (user_id, criteria_text)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE
            SET criteria_text = EXCLUDED.criteria_text
            """,
            (user_id, criteria_text),
        )
    logger.info(f"Saved criteria for user {user_id}")


def get_distinct_companies() -> list[str]:
    """Return all distinct, non-empty company names seen in the jobs table, alphabetically."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT company FROM jobs WHERE company IS NOT NULL AND company != '' ORDER BY company"
        )
        rows = cur.fetchall()
    return [row[0] for row in rows]


def get_followed_companies(user_id: int) -> list[str]:
    """Return the list of companies the user follows, alphabetically."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT company FROM user_companies WHERE user_id = %s ORDER BY company", (user_id,))
        rows = cur.fetchall()
    return [row[0] for row in rows]


def set_followed_companies(user_id: int, companies: list[str]) -> None:
    """Replace the user's followed companies with the given list."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM user_companies WHERE user_id = %s", (user_id,))
        if companies:
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO user_companies (user_id, company) VALUES %s",
                [(user_id, company) for company in companies],
            )
    logger.info(f"Set {len(companies)} followed companies for user {user_id}")


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
    Jobs categorized as 'skip' get tier='skip'.
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



