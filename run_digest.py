"""
Daily digest pipeline:
  1. Fetch unread Gmail alerts → enrich descriptions → save to DB
  2. Query DB for jobs from last 24h
  3. Rank via Claude
  4. Send digest email
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
from src.database import create_tables, insert_jobs, fetch_recent_jobs
from src.ranker import rank_jobs
from src.email_digest import send_digest


def main():
    create_tables()

    # Step 1: fetch
    logger.info("Fetching unread Gmail alerts...")
    fetcher = GmailFetcher()
    jobs = fetcher.fetch_all_jobs()
    logger.info(f"Found {len(jobs)} new jobs")

    if jobs:
        logger.info("Enriching job descriptions...")
        fetcher.enrich_with_descriptions(jobs)
        inserted = insert_jobs(jobs)
        logger.info(f"Saved {inserted} new jobs to database")
    else:
        logger.info("No new emails — skipping fetch step")

    # Step 2: load last 24h from DB
    recent = fetch_recent_jobs(hours=24)
    if not recent:
        logger.info("No jobs in the last 24h — nothing to rank or send")
        sys.exit(0)

    # Step 3: rank
    logger.info(f"Ranking {len(recent)} jobs...")
    result = rank_jobs(recent)
    logger.info(f"Ranked: {len(result.top)} top, {len(result.next_best)} next best")

    # Step 4: send
    sent = send_digest(result)
    if sent:
        logger.info("Digest sent successfully")
    else:
        logger.info("Nothing to send (all jobs dropped below floor score)")


if __name__ == "__main__":
    main()
