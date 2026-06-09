"""
Daily digest pipeline:
  1. Fetch unread Gmail alerts → enrich descriptions → save to DB
  2. Query DB for all undigested jobs (digested_at IS NULL)
  3. Rank via Claude → save tier / tier_order / reason / ranked_at back to DB
  4. Send digest email → mark jobs as digested
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
from src.database import create_tables, insert_jobs, fetch_undigested_jobs, mark_jobs_digested, save_ranking
from src.job_class import Job
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
        logger.info("Enriching jobs...")
        fetcher.enrich(jobs)
        seen: dict[str, Job] = {}
        for job in jobs:
            if job.url not in seen:
                seen[job.url] = job
        jobs = list(seen.values())
        inserted = insert_jobs(jobs)
        logger.info(f"Saved {inserted} new jobs to database")
    else:
        logger.info("No new emails — skipping fetch step")

    # Step 2: load all undigested jobs from DB
    recent = fetch_undigested_jobs()
    if not recent:
        logger.info("No undigested jobs — nothing to rank or send")
        sys.exit(0)

    # Step 3: rank and write result to database
    logger.info(f"Ranking {len(recent)} jobs...")
    result = rank_jobs(recent)
    logger.info(f"Ranked: {len(result.top)} top, {len(result.next_best)} next best")
    save_ranking(result, recent)

    # Step 4: send — only mark digested after a confirmed send
    sent = send_digest(result)
    if sent:
        url_hashes = [j.url_hash for j in recent]
        mark_jobs_digested(url_hashes)
        logger.info("Digest sent successfully")
    else:
        logger.info("Nothing to send (all jobs categorized as skip)")


if __name__ == "__main__":
    main()
