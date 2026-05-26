#!/usr/bin/env python3
# One-time import of job postings by URL directly into the database.
# Scrapes each URL, extracts fields via JSON-LD / ATS heuristics, lets you
# confirm or override each field, then inserts into the jobs table.
#
# Usage:
#   python import_jobs.py https://jobs.ashbyhq.com/company/job-id
#   python import_jobs.py url1 url2 url3 ...
#   python import_jobs.py url1 --add-to-eval   # also append to eval/test_jobs.json

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))

from src.database import insert_jobs
from src.job_class import Job
from src.parsers import extract_company_from_url, extract_job_fields

SCRAPE_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
}

EVAL_TEST_JOBS = Path("eval/test_jobs.json")


def prompt_field(label: str, detected: str) -> str:
    """Show auto-detected value; user presses Enter to accept or types a replacement."""
    display = detected if detected else '(not detected)'
    user_input = input(f"  {label:<12} {display}\n{'':>14}[enter to keep, or type override]: ").strip()
    return user_input if user_input else detected


def fetch_and_parse(url: str, session: requests.Session) -> dict:
    resp = session.get(url, timeout=20, allow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'lxml')
    fields = extract_job_fields(soup)
    if not fields['company']:
        fields['company'] = extract_company_from_url(url)
    return fields


def append_to_eval(job: Job) -> None:
    record = {
        "url_hash":    job.url_hash,
        "title":       job.title,
        "company":     job.company,
        "location":    job.location,
        "url":         job.url,
        "source":      job.source,
        "raw_snippet": job.raw_snippet,
        "description": job.description,
        "fetched_at":  job.fetched_at.isoformat() if isinstance(job.fetched_at, datetime) else job.fetched_at,
    }
    existing = []
    if EVAL_TEST_JOBS.exists():
        with open(EVAL_TEST_JOBS, encoding='utf-8') as f:
            existing = json.load(f)
    if any(r['url_hash'] == job.url_hash for r in existing):
        print("  (already in eval/test_jobs.json, skipping)")
        return
    existing.append(record)
    with open(EVAL_TEST_JOBS, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    print(f"  Added to {EVAL_TEST_JOBS}")


def main():
    parser = argparse.ArgumentParser(
        description='Import job postings by URL into the database.'
    )
    parser.add_argument('urls', nargs='+', help='ATS job posting URLs to import')
    parser.add_argument('--add-to-eval', action='store_true',
                        help='Also append each imported job to eval/test_jobs.json')
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(SCRAPE_HEADERS)

    for i, url in enumerate(args.urls):
        if i > 0:
            time.sleep(1.5)

        print(f"\n{'─' * 60}")
        print(f"URL: {url}")

        try:
            fields = fetch_and_parse(url, session)
        except Exception as e:
            print(f"  ERROR fetching page: {e}")
            print("  Skipping — you can try again or import manually.")
            continue

        desc_len = len(fields['description'])
        print(f"  (description: {desc_len} chars extracted)\n")

        title    = prompt_field("Title",    fields['title'])
        company  = prompt_field("Company",  fields['company'])
        location = prompt_field("Location", fields['location'])
        source   = prompt_field("Source",   "manual")

        if not title:
            print("  Title is required — skipping.")
            continue

        job = Job(
            title=title,
            company=company,
            location=location,
            url=url,
            source=source,
            raw_snippet='',
            description=fields['description'],
            fetched_at=datetime.now(timezone.utc),
        )

        inserted = insert_jobs([job])
        if inserted:
            print(f"  Inserted into database.")
        else:
            print(f"  Already exists in database (url_hash collision), skipping insert.")

        if args.add_to_eval:
            append_to_eval(job)

    print(f"\n{'─' * 60}")
    print("Done.")


if __name__ == '__main__':
    main()
