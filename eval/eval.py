#!/usr/bin/env python3
# Prompt evaluation harness.
# Loads test jobs from eval/test_jobs.json, runs rank_jobs(), compares against
# eval/ground_truth.json, prints a results table, and saves the run to eval/runs/.
#
# Usage:
#   python eval/eval.py
#
# After seeding for the first time, create eval/ground_truth.json:
#   python eval/eval.py --init-ground-truth

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.job_class import Job
from src.ranker import rank_jobs

TEST_JOBS_PATH   = Path(__file__).parent / "test_jobs.json"
GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"
RUNS_DIR          = Path(__file__).parent / "runs"
CRITERIA_PATH     = Path(__file__).parent.parent / "config" / "criteria.txt"


def load_test_jobs() -> list[Job]:
    with open(TEST_JOBS_PATH, encoding='utf-8') as f:
        records = json.load(f)
    jobs = []
    for r in records:
        job = Job(
            title=r['title'],
            company=r['company'],
            location=r['location'],
            url=r['url'],
            source=r['source'],
            raw_snippet=r.get('raw_snippet', ''),
            description=r.get('description', ''),
        )
        jobs.append(job)
    return jobs


def init_ground_truth(jobs: list[Job]) -> None:
    if GROUND_TRUTH_PATH.exists():
        print(f"{GROUND_TRUTH_PATH} already exists. Delete it first to regenerate.")
        return
    template = {}
    for job in jobs:
        template[job.url_hash] = {
            "tier": "top",  # change to: top | next_best | skip
            "notes": f"{job.title} at {job.company}"
        }
    with open(GROUND_TRUTH_PATH, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2)
    print(f"Created {GROUND_TRUTH_PATH}")
    print("Edit it: set each 'tier' to top, next_best, or skip. Then run: python eval/eval.py")


def tier_symbol(tier: str) -> str:
    return {'top': 'TOP', 'next_best': 'NEXT', 'skip': 'skip'}.get(tier, tier)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--init-ground-truth', action='store_true',
                        help='Generate a ground_truth.json template from test_jobs.json')
    args = parser.parse_args()

    if not TEST_JOBS_PATH.exists():
        print("eval/test_jobs.json not found. Run: python seed_eval.py")
        sys.exit(1)

    jobs = load_test_jobs()

    if args.init_ground_truth:
        init_ground_truth(jobs)
        sys.exit(0)

    if not GROUND_TRUTH_PATH.exists():
        print("eval/ground_truth.json not found.")
        print("Run: python eval/eval.py --init-ground-truth  then fill in the tiers.")
        sys.exit(1)

    with open(GROUND_TRUTH_PATH, encoding='utf-8') as f:
        ground_truth = json.load(f)

    criteria_snapshot = CRITERIA_PATH.read_text(encoding='utf-8') if CRITERIA_PATH.exists() else ''
    criteria_mtime = datetime.fromtimestamp(CRITERIA_PATH.stat().st_mtime, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if CRITERIA_PATH.exists() else 'unknown'

    print(f"\nRunning ranker on {len(jobs)} test jobs...")
    result = rank_jobs(jobs)

    ranked_by_hash = {}
    for rj in result.top + result.next_best:
        ranked_by_hash[rj.job.url_hash] = rj

    run_timestamp = datetime.now(timezone.utc)
    run_records = []
    correct = 0
    top_predicted, top_expected = 0, 0

    col = (36, 20, 10, 10, 5)
    header = (
        f"{'JOB':<{col[0]}}  "
        f"{'COMPANY':<{col[1]}}  "
        f"{'GOT':^{col[2]}}  "
        f"{'EXPECTED':^{col[3]}}  "
        f"{'':^{col[4]}}"
    )
    divider = '-' * len(header)
    print(f"\nEVAL RUN {run_timestamp.strftime('%Y-%m-%d %H:%M:%S')}  |  criteria.txt modified: {criteria_mtime}")
    print(divider)
    print(header)
    print(divider)

    for job in jobs:
        rj = ranked_by_hash.get(job.url_hash)
        actual_tier = rj.tier if rj else 'skip'
        reason = rj.reason if rj else ''

        gt = ground_truth.get(job.url_hash, {})
        expected_tier = gt.get('tier', '?') if isinstance(gt, dict) else gt

        match = actual_tier == expected_tier
        if match:
            correct += 1
        if actual_tier == 'top':
            top_predicted += 1
        if expected_tier == 'top':
            top_expected += 1

        mark = '✓' if match else '✗'
        title = job.title[:col[0]] if len(job.title) > col[0] else job.title
        company = job.company[:col[1]] if len(job.company) > col[1] else job.company

        print(
            f"{title:<{col[0]}}  "
            f"{company:<{col[1]}}  "
            f"{tier_symbol(actual_tier):^{col[2]}}  "
            f"{tier_symbol(expected_tier):^{col[3]}}  "
            f"{mark:^{col[4]}}"
        )
        if rj and not match:
            print(f"       reason: {reason}")

        run_records.append({
            "url_hash":      job.url_hash,
            "title":         job.title,
            "company":       job.company,
            "actual_tier":   actual_tier,
            "expected_tier": expected_tier,
            "match":         match,
            "reason":        reason,
        })

    top_correct = sum(
        1 for r in run_records
        if r['expected_tier'] == 'top' and r['actual_tier'] == 'top'
    )
    nb_correct = sum(
        1 for r in run_records
        if r['expected_tier'] == 'next_best' and r['actual_tier'] == 'next_best'
    )
    nb_predicted = sum(1 for r in run_records if r['actual_tier'] == 'next_best')
    nb_expected  = sum(1 for r in run_records if r['expected_tier'] == 'next_best')

    top_precision = top_correct / top_predicted if top_predicted else 0.0
    top_recall    = top_correct / top_expected  if top_expected  else 0.0
    nb_precision  = nb_correct  / nb_predicted  if nb_predicted  else 0.0
    nb_recall     = nb_correct  / nb_expected   if nb_expected   else 0.0
    agreement     = correct / len(jobs) if jobs else 0.0

    print(divider)
    print(f"Agreement:         {correct}/{len(jobs)} ({agreement:.0%})")
    print(f"Top precision:     {top_correct}/{top_predicted} ({top_precision:.0%})")
    print(f"Top recall:        {top_correct}/{top_expected} ({top_recall:.0%})")
    print(f"Next-best precision: {nb_correct}/{nb_predicted} ({nb_precision:.0%})")
    print(f"Next-best recall:    {nb_correct}/{nb_expected} ({nb_recall:.0%})")
    print()

    RUNS_DIR.mkdir(exist_ok=True)
    run_file = RUNS_DIR / f"{run_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    with open(run_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": run_timestamp.isoformat(),
            "criteria_mtime": criteria_mtime,
            "criteria_snapshot": criteria_snapshot,
            "metrics": {
                "agreement": round(agreement, 3),
                "top_precision": round(top_precision, 3),
                "top_recall": round(top_recall, 3),
                "next_best_precision": round(nb_precision, 3),
                "next_best_recall": round(nb_recall, 3),
                "correct": correct,
                "total": len(jobs),
            },
            "results": run_records,
        }, f, indent=2)
    print(f"Run saved to {run_file}")


if __name__ == '__main__':
    main()
