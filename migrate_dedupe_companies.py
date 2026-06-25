"""
One-time migration: add career_site_url, merge duplicate companies, populate URLs,
and add new companies from Google Alerts.
"""
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

from src.database import _connect, create_tables

# career_site_url for each canonical company (extracted from Google Alerts screenshots)
CAREER_URLS = {
    "Abridge": "jobs.ashbyhq.com/abridge/",
    "Airtable": "job-boards.greenhouse.io/airtable/jobs/",
    "Anthropic": "job-boards.greenhouse.io/anthropic",
    "Brex": "www.brex.com/careers/",
    "Cloudflare": "job-boards.greenhouse.io/cloudflare/jobs/",
    "Cognition": "jobs.ashbyhq.com/cognition/",
    "Cohere": "jobs.ashbyhq.com/cohere/",
    "Commure": "jobs.ashbyhq.com/Commure/",
    "Decagon": "jobs.ashbyhq.com/decagon/",
    "Deel": "www.deel.com/careers/position/",
    "Deepmind": "job-boards.greenhouse.io/deepmind/jobs/",
    "Figma": "job-boards.greenhouse.io/figma/jobs/",
    "Fractional Ai": "jobs.ashbyhq.com/fractional-ai/",
    "Gamma": "jobs.ashbyhq.com/gamma/",
    "Glean": "job-boards.greenhouse.io/gleanwork/jobs/",
    "Google": "www.google.com/about/careers/applications/",
    "Harvey": "jobs.ashbyhq.com/harvey/",
    "Hubspot": "hubspot.com/careers/jobs/",
    "Klaviyo": "klaviyo.com/careers/jobs/",
    "Legora": "jobs.ashbyhq.com/legora/",
    "Lifeatcanva": "www.lifeatcanva.com/en/jobs/",
    "Meta": "www.metacareers.com/profile/job_details",
    "Miro": "miro.com/careers/vacancy/",
    "Monday": "monday.com/careers/",
    "Mongodb": "mongodb.com/careers/jobs/",
    "Notion": "jobs.ashbyhq.com/notion/",
    "OpenAI": "openai.com/careers/",
    "Perplexity": "jobs.ashbyhq.com/perplexity/",
    "Prime Intellect": "jobs.ashbyhq.com/PrimeIntellect/",
    "Ramp": "jobs.ashbyhq.com/ramp/",
    "Reflectionai": "jobs.ashbyhq.com/reflectionai/",
    "Replit": "jobs.ashbyhq.com/replit/",
    "Rubrik": "rubrik.com/company/careers/departments/",
    "Samsara": "samsara.com/company/careers/roles/",
    "Sierra": "jobs.ashbyhq.com/Sierra/",
    "Vanta": "jobs.ashbyhq.com/vanta/",
    "Vercel": "vercel.com/careers/",
    "Wiz": "www.wiz.io/careers/job/",
    "Writer": "jobs.ashbyhq.com/writer/",
    "Netlify": "job-boards.greenhouse.io/netlify/jobs/",
}

# Duplicates to merge: canonical_name -> [duplicate names to absorb]
MERGES = {
    "Deepmind": ["Google DeepMind"],
    "Glean": ["Gleanwork"],
    "Meta": ["Metacareers"],
    "OpenAI": ["Openai", "openai"],
    "Prime Intellect": ["Primeintellect"],
    "Sierra": ["Sierra Studio"],
}

# New companies from Google Alerts not yet in DB
NEW_COMPANIES = {
    "Credal": "jobs.ashbyhq.com/credal/",
    "Moveworks": "moveworks.com/us/en/company/careers/",
    "Navan": "navan.com/careers/openings/",
    "Suki": "suki.ai/open-positions/",
    "Expensify": "we.are.expensify.com/",
}


def main():
    create_tables()

    with _connect() as conn, conn.cursor() as cur:
        # 1. Merge duplicates: reassign jobs and user_companies, then delete the duplicate row
        for canonical, dupes in MERGES.items():
            cur.execute("SELECT id FROM companies WHERE name = %s", (canonical,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Canonical company '{canonical}' not found, skipping merge")
                continue
            canonical_id = row[0]

            for dupe_name in dupes:
                cur.execute("SELECT id FROM companies WHERE name = %s", (dupe_name,))
                dupe_row = cur.fetchone()
                if not dupe_row:
                    logger.info(f"  Dupe '{dupe_name}' not found, skipping")
                    continue
                dupe_id = dupe_row[0]

                # Reassign jobs
                cur.execute("UPDATE jobs SET company_id = %s WHERE company_id = %s", (canonical_id, dupe_id))
                jobs_moved = cur.rowcount

                # Reassign user_companies (ignore conflicts if user already follows canonical)
                cur.execute(
                    "UPDATE user_companies SET company_id = %s WHERE company_id = %s AND user_id NOT IN "
                    "(SELECT user_id FROM user_companies WHERE company_id = %s)",
                    (canonical_id, dupe_id, canonical_id),
                )
                follows_moved = cur.rowcount
                cur.execute("DELETE FROM user_companies WHERE company_id = %s", (dupe_id,))

                cur.execute("DELETE FROM companies WHERE id = %s", (dupe_id,))
                logger.info(f"  Merged '{dupe_name}' (id={dupe_id}) into '{canonical}' (id={canonical_id}): {jobs_moved} jobs, {follows_moved} follows moved")

        # 2. Set career_site_url on existing companies
        for name, url in CAREER_URLS.items():
            cur.execute("UPDATE companies SET career_site_url = %s WHERE name = %s", (url, name))
            if cur.rowcount:
                logger.info(f"  Set URL for '{name}': {url}")

        # 3. Add new companies
        for name, url in NEW_COMPANIES.items():
            cur.execute(
                "INSERT INTO companies (name, career_site_url, tracked) VALUES (%s, %s, TRUE) ON CONFLICT (name) DO UPDATE SET career_site_url = EXCLUDED.career_site_url, tracked = TRUE",
                (name, url),
            )
            logger.info(f"  Added new company '{name}': {url}")

    logger.info("Migration complete")

    # Print summary
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT name, career_site_url, tracked FROM companies WHERE tracked = TRUE ORDER BY name")
        rows = cur.fetchall()
    logger.info(f"\n{'Name':<25} {'Career Site URL':<55} {'Tracked'}")
    logger.info("-" * 90)
    for name, url, tracked in rows:
        logger.info(f"{name:<25} {(url or '(none)'):<55} {tracked}")


if __name__ == "__main__":
    main()
