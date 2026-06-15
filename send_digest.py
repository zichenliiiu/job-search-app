"""
Digest pipeline (run once per day, per user):
  For each user:
    1. Find jobs from companies they follow that haven't been ranked for them yet
    2. Rank via Claude against the user's own criteria → save to user_job_rankings
    3. Email the user their digest
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

from src.database import (
    create_tables,
    get_all_users,
    get_followed_companies,
    get_user_criteria,
    get_unranked_jobs_for_user,
    save_user_ranking,
)
from src.ranker import rank_jobs
from src.email_digest import send_digest


def main():
    create_tables()

    users = get_all_users()
    if not users:
        logger.info("No users — nothing to do")
        sys.exit(0)

    for user in users:
        user_id, email = user["id"], user["email"]

        if not get_followed_companies(user_id):
            logger.info(f"{email}: no followed companies, skipping")
            continue

        criteria = get_user_criteria(user_id)
        top_description = criteria["top_description"]
        next_best_description = criteria["next_best_description"]
        if not top_description.strip() and not next_best_description.strip():
            logger.info(f"{email}: no ranking criteria set, skipping")
            continue

        jobs = get_unranked_jobs_for_user(user_id)
        if not jobs:
            logger.info(f"{email}: no new jobs to rank")
            continue

        logger.info(f"{email}: ranking {len(jobs)} jobs...")
        result = rank_jobs(jobs, top_description=top_description, next_best_description=next_best_description)
        logger.info(f"{email}: ranked {len(result.top)} top, {len(result.next_best)} next best")
        save_user_ranking(user_id, result, jobs)

        if send_digest(result, recipient_email=email):
            logger.info(f"{email}: digest sent")
        else:
            logger.info(f"{email}: nothing to send (all jobs categorized as skip)")


if __name__ == "__main__":
    main()
