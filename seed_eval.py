#!/usr/bin/env python3
# Build or append to eval/test_jobs.json by passing job IDs from Supabase.
#
# Usage:
#   python seed_eval.py 1 47 203 891          # space-separated
#   python seed_eval.py 1,47,203,891          # comma-separated
#   python seed_eval.py 1 47 --append         # add to existing test set

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database import fetch_jobs_by_ids

OUT_PATH = Path("eval/test_jobs.json")


def parse_ids(args: list[str]) -> list[int]:
    ids = []
    for token in args:
        for part in token.split(','):
            part = part.strip()
            if part:
                ids.append(int(part))
    return ids


def job_to_record(job) -> dict:
    fetched_at = job.fetched_at
    if isinstance(fetched_at, datetime):
        fetched_at = fetched_at.isoformat()
    return {
        "url_hash":    job.url_hash,
        "title":       job.title,
        "company":     job.company,
        "location":    job.location,
        "url":         job.url,
        "source":      job.source,
        "raw_snippet": job.raw_snippet,
        "description": job.description,
        "fetched_at":  fetched_at,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Seed eval/test_jobs.json with jobs selected by ID from Supabase."
    )
    parser.add_argument('ids', nargs='+', help='Job IDs (space or comma separated)')
    parser.add_argument('--append', action='store_true',
                        help='Add to existing test_jobs.json instead of overwriting')
    args = parser.parse_args()

    ids = parse_ids(args.ids)
    if not ids:
        print("No valid IDs provided.")
        sys.exit(1)

    jobs = fetch_jobs_by_ids(ids)
    if not jobs:
        print(f"No jobs found for IDs: {ids}")
        sys.exit(1)

    new_records = [job_to_record(j) for j in jobs]

    if args.append and OUT_PATH.exists():
        with open(OUT_PATH, encoding='utf-8') as f:
            existing = json.load(f)
        existing_hashes = {r['url_hash'] for r in existing}
        added = [r for r in new_records if r['url_hash'] not in existing_hashes]
        records = existing + added
        print(f"Appended {len(added)} jobs ({len(new_records) - len(added)} already present)")
    else:
        records = new_records

    OUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(records)} jobs to {OUT_PATH}")
    if not (Path("eval") / "ground_truth.json").exists():
        print("\nNext: create ground truth labels:")
        print("  python eval/eval.py --init-ground-truth")


if __name__ == '__main__':
    main()
