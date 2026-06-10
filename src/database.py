from __future__ import annotations

# Postgres persistence layer (Supabase).
# Called by fetch_jobs.py, send_digest.py, and test_fetch.py.
#
#   create_tables()                  creates the jobs table if it doesn't exist (safe to call on every run)
#   insert_jobs(jobs)                upserts a list[Job], skips duplicates by url_hash → returns new row count
#   fetch_undigested_jobs()          returns all jobs not yet sent in a digest (digested_at IS NULL), newest first
#   mark_jobs_digested(url_hashes)   stamps digested_at=NOW() on the given rows after a successful digest send
#   save_ranking(result, all_jobs)   writes tier/tier_order/reason/ranked_at to the ranked rows; marks the rest 'skip'
#   get_all_companies()              returns all companies in the registry with their tracked status
#   add_company(name, tracked)       adds a company to the registry (or updates tracked status if it exists)
#   register_companies(names)        adds any unrecognized names to the registry as untracked (pending)
#   set_company_tracked(name, x)     marks a company as tracked (Google Alert on its career site) or not

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

CREATE_COMPANIES_TABLE = """
CREATE TABLE IF NOT EXISTS companies (
    id            SERIAL PRIMARY KEY,
    name          TEXT UNIQUE NOT NULL,
    tracked       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_USER_JOB_RANKINGS_TABLE = """
CREATE TABLE IF NOT EXISTS user_job_rankings (
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id        INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    tier          TEXT NOT NULL,
    tier_order    INTEGER,
    reason        TEXT,
    ranked_at     TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, job_id)
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
        cur.execute(CREATE_COMPANIES_TABLE)
        cur.execute(CREATE_USER_JOB_RANKINGS_TABLE)
    logger.info("Database tables ready")


def get_all_users() -> list[dict]:
    """Return all registered users."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, provider, provider_sub, email, name FROM users")
        rows = cur.fetchall()
    return [
        {"id": r[0], "provider": r[1], "provider_sub": r[2], "email": r[3], "name": r[4]}
        for r in rows
    ]


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


def get_followed_companies(user_id: int) -> list[str]:
    """Return the list of companies the user follows, alphabetically."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT company FROM user_companies WHERE user_id = %s ORDER BY company", (user_id,))
        rows = cur.fetchall()
    return [row[0] for row in rows]


def set_followed_companies(user_id: int, companies: list[str]) -> None:
    """Replace the user's followed companies with the given list."""
    register_companies(companies)
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM user_companies WHERE user_id = %s", (user_id,))
        if companies:
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO user_companies (user_id, company) VALUES %s",
                [(user_id, company) for company in companies],
            )
    logger.info(f"Set {len(companies)} followed companies for user {user_id}")


def register_companies(names: list[str]) -> None:
    """Add any unrecognized company names to the registry as untracked (pending).

    Existing companies, and their tracked status, are left untouched.
    """
    if not names:
        return
    with _connect() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO companies (name, tracked) VALUES %s ON CONFLICT (name) DO NOTHING",
            [(name, False) for name in names],
        )


def get_all_companies() -> list[dict]:
    """Return all companies, alphabetically, with their tracked status."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, tracked FROM companies ORDER BY name")
        rows = cur.fetchall()
    return [{"id": r[0], "name": r[1], "tracked": r[2]} for r in rows]


def add_company(name: str, tracked: bool = False) -> None:
    """Add a company to the registry, or update its tracked status if it already exists."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO companies (name, tracked)
            VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE SET tracked = EXCLUDED.tracked
            """,
            (name, tracked),
        )
    logger.info(f"Added company '{name}' (tracked={tracked})")


def set_company_tracked(name: str, tracked: bool) -> None:
    """Mark a company as tracked (Google Alert set on its career site) or not."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("UPDATE companies SET tracked = %s WHERE name = %s", (tracked, name))
    logger.info(f"Set company '{name}' tracked={tracked}")


def migrate_drop_global_ranking_columns() -> None:
    """One-time migration: drop the old global ranking/digest columns from jobs.

    These were superseded by the per-user user_job_rankings table.
    """
    stmts = [
        "ALTER TABLE jobs DROP COLUMN IF EXISTS tier",
        "ALTER TABLE jobs DROP COLUMN IF EXISTS tier_order",
        "ALTER TABLE jobs DROP COLUMN IF EXISTS reason",
        "ALTER TABLE jobs DROP COLUMN IF EXISTS ranked_at",
        "ALTER TABLE jobs DROP COLUMN IF EXISTS digested_at",
    ]
    with _connect() as conn, conn.cursor() as cur:
        for stmt in stmts:
            cur.execute(stmt)
    logger.info("Dropped global ranking/digest columns from jobs table")


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


def get_unranked_jobs_for_user(user_id: int) -> list[Job]:
    """Return jobs from companies the user follows that haven't been ranked for them yet."""
    sql = """
        SELECT j.id, j.url_hash, j.title, j.company, j.location, j.url, j.source, j.raw_snippet, j.description, j.fetched_at
        FROM jobs j
        JOIN user_companies uc ON uc.user_id = %s AND uc.company = j.company
        LEFT JOIN user_job_rankings ujr ON ujr.user_id = %s AND ujr.job_id = j.id
        WHERE ujr.job_id IS NULL
        ORDER BY j.fetched_at DESC
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id, user_id))
        rows = cur.fetchall()

    jobs = []
    for row in rows:
        job_id, url_hash, title, company, location, url, source, raw_snippet, description, fetched_at = row
        job = Job(
            title=title or '',
            company=company or '',
            location=location or '',
            url=url,
            source=source,
            raw_snippet=raw_snippet or '',
            description=description or '',
            fetched_at=fetched_at,
            id=job_id,
        )
        jobs.append(job)

    logger.info(f"Found {len(jobs)} unranked jobs for user {user_id}")
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


def save_user_ranking(user_id: int, result, all_jobs: list[Job]) -> None:
    """Write a user's ranking results to user_job_rankings.

    Ranked jobs (top / next_best) get tier, tier_order, reason, and ranked_at.
    The remaining jobs from all_jobs are recorded as tier='skip' so they aren't re-ranked.
    """
    now = datetime.now(timezone.utc)
    ranked_ids: set[int] = set()
    rows = []

    for order, ranked_job in enumerate(result.top, start=1):
        rows.append((user_id, ranked_job.job.id, 'top', order, ranked_job.reason, now))
        ranked_ids.add(ranked_job.job.id)

    for order, ranked_job in enumerate(result.next_best, start=1):
        rows.append((user_id, ranked_job.job.id, 'next_best', order, ranked_job.reason, now))
        ranked_ids.add(ranked_job.job.id)

    for job in all_jobs:
        if job.id not in ranked_ids:
            rows.append((user_id, job.id, 'skip', None, None, now))

    with _connect() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO user_job_rankings (user_id, job_id, tier, tier_order, reason, ranked_at)
            VALUES %s
            ON CONFLICT (user_id, job_id) DO NOTHING
            """,
            rows,
            template="(%s, %s, %s, %s, %s, %s::timestamptz)",
        )

    skip_count = len(all_jobs) - len(ranked_ids)
    logger.info(
        f"Saved ranking for user {user_id}: {len(result.top)} top, {len(result.next_best)} next_best, {skip_count} skip"
    )



