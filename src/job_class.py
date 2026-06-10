# Shared data model.
# Defines the Job dataclass used across gmail_fetcher, parsers, database, and ranker.
# url_hash is auto-generated from the URL and used as the deduplication key in Postgres.

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str  # 'linkedin' or 'google_alerts'
    raw_snippet: str = ''
    description: str = ''
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: int | None = None  # jobs.id primary key, set when loaded from the DB
    url_hash: str = field(init=False)

    def __post_init__(self):
        self.url_hash = hashlib.md5(self.url.encode()).hexdigest()
