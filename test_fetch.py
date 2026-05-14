"""
Quick test run for GmailFetcher.
Fetches unread LinkedIn + Google Alert emails, prints a summary,
and saves full output to data/test_fetch_output.json.
"""
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from src.gmail_fetcher import GmailFetcher

def main():
    print("Authenticating with Gmail...")
    fetcher = GmailFetcher()

    print("Fetching jobs...")
    jobs = fetcher.fetch_all_jobs()

    print(f"\n{'='*50}")
    print(f"Found {len(jobs)} jobs total")
    print(f"{'='*50}\n")

    linkedin = [j for j in jobs if j.source == 'linkedin']
    google = [j for j in jobs if j.source == 'google_alerts']
    print(f"  LinkedIn alerts:  {len(linkedin)}")
    print(f"  Google alerts:    {len(google)}")

    print(f"\nFetching job descriptions (this will take ~{len(jobs) * 1.5:.0f}s)...")
    fetcher.enrich_with_descriptions(jobs)

    # Print a quick preview
    print("\n--- PREVIEW (first 5) ---")
    for job in jobs[:5]:
        print(f"[{job.source}] {job.title} @ {job.company} | {job.location}")
        print(f"  {job.url[:80]}...")
        if job.description:
            print(f"  Description: {job.description[:150]}...")
        print()

    # Serialize to JSON (datetime → ISO string)
    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Not serializable: {type(obj)}")

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total": len(jobs),
        "linkedin_count": len(linkedin),
        "google_alerts_count": len(google),
        "jobs": [asdict(j) for j in jobs],
    }

    out_path = "data/test_fetch_output.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=serialize)

    print(f"Full output saved to: {out_path}")

    fetcher.mark_last_batch_unread()
    print("Emails marked as unread for next test run.")

if __name__ == "__main__":
    main()
