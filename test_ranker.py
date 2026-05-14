"""
Fetch all jobs from the database, rank them, and save a human-readable report to data/.
Opens two sections side-by-side: ranked output and the raw unranked list for comparison.
"""
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from src.database import fetch_all_jobs
from src.ranker import rank_jobs, RankerResult
from src.email_digest import send_digest

OUT_PATH = "data/ranked_output.txt"


def _divider(char="-", width=80):
    return char * width


def _job_line(job, index=None):
    prefix = f"{index:>3}. " if index is not None else "     "
    loc = f" | {job.location}" if job.location else ""
    return f"{prefix}{job.title} @ {job.company}{loc}\n     {job.url[:90]}"


def write_report(jobs, result: RankerResult, path: str):
    lines = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append(_divider("="))
    lines.append(f"JOB RANKING REPORT — {now}")
    lines.append(f"Total jobs in database: {len(jobs)}")
    lines.append(f"Top options (score ≥ 75): {len(result.top)}")
    lines.append(f"Next best (score 40–74): {len(result.next_best)}")
    lines.append(f"Dropped (score < 40):    {len(jobs) - len(result.top) - len(result.next_best)}")
    lines.append(_divider("="))

    # --- RANKED OUTPUT ---
    lines.append("")
    lines.append("RANKED RESULTS")
    lines.append(_divider())

    if result.top:
        lines.append("")
        lines.append("★  TOP OPTIONS  (score ≥ 75)")
        lines.append(_divider("-", 40))
        for i, rj in enumerate(result.top, 1):
            loc = f" | {rj.job.location}" if rj.job.location else ""
            lines.append(f"  {i:>2}. [{rj.score}/100] {rj.job.title} @ {rj.job.company}{loc}")
            lines.append(f"       {rj.reason}")
            lines.append(f"       {rj.job.url[:90]}")
            lines.append("")
    else:
        lines.append("")
        lines.append("  (no jobs cleared the Top Options threshold today)")
        lines.append("")

    if result.next_best:
        lines.append("")
        lines.append("◆  NEXT BEST  (score 40–74)")
        lines.append(_divider("-", 40))
        for i, rj in enumerate(result.next_best, 1):
            loc = f" | {rj.job.location}" if rj.job.location else ""
            lines.append(f"  {i:>2}. [{rj.score}/100] {rj.job.title} @ {rj.job.company}{loc}")
            lines.append(f"       {rj.reason}")
            lines.append(f"       {rj.job.url[:90]}")
            lines.append("")
    else:
        lines.append("")
        lines.append("  (no jobs in the Next Best bucket)")
        lines.append("")

    # --- UNRANKED LIST ---
    lines.append("")
    lines.append(_divider("="))
    lines.append("UNRANKED LIST (all jobs, newest first)")
    lines.append(_divider())
    lines.append("")
    for i, job in enumerate(jobs, 1):
        lines.append(_job_line(job, i))
        if job.description:
            snippet = job.description[:200].replace("\n", " ")
            lines.append(f"     {snippet}...")
        lines.append("")

    report = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)

    return report


def main():
    print("Fetching jobs from database...")
    jobs = fetch_all_jobs()
    if not jobs:
        print("No jobs in database. Run test_fetch.py first.")
        return

    print(f"Found {len(jobs)} jobs. Running ranker (this may take a minute)...")
    result = rank_jobs(jobs)

    print(f"\nResults: {len(result.top)} top options, {len(result.next_best)} next best")
    print(f"Writing report to {OUT_PATH}...")

    import os
    os.makedirs("data", exist_ok=True)
    write_report(jobs, result, OUT_PATH)
    print(f"Done. Open {OUT_PATH} to review.")

    print("\nSending digest email...")
    sent = send_digest(result)
    if sent:
        print("Email sent — check your inbox.")
    else:
        print("Nothing to send (all jobs dropped).")


if __name__ == "__main__":
    main()
