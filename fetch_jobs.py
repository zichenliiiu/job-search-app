"""
Fetch pipeline (no AI, safe to run as often as you like):
  1. Fetch unread Gmail alerts → enrich descriptions → save to DB
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

from src.gmail_fetcher import GmailFetcher
from src.database import create_tables, insert_jobs
from src.job_class import Job


def main():
    create_tables()

    logger.info("Fetching unread Gmail alerts...")
    fetcher = GmailFetcher()
    jobs = fetcher.fetch_all_jobs()
    logger.info(f"Found {len(jobs)} new jobs")

    if not jobs:
        logger.info("No new emails — nothing to insert")
        sys.exit(0)

    logger.info("Enriching jobs...")
    fetcher.enrich(jobs)
    seen: dict[str, Job] = {}
    for job in jobs:
        if job.url not in seen:
            seen[job.url] = job
    jobs = list(seen.values())

    inserted = insert_jobs(jobs)
    logger.info(f"Saved {inserted} new jobs to database")


if __name__ == "__main__":
    main()
