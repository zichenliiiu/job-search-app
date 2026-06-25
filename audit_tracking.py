"""
Monthly audit: check which tracked companies have jobs in the DB.

For each company where tracked=True, sets tracking_working=True if at least
one job exists, False otherwise. Sends an email listing companies where
tracking is not working so you can fix the Google Alert.

Usage:
    python audit_tracking.py              # audit + email if problems found
    python audit_tracking.py --dry-run    # print results, don't update DB or send email
"""
import logging
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

from config.config import GMAIL_APP_PASSWORD, RECIPIENT_EMAIL
from src.database import _connect, create_tables


def audit_tracking(dry_run: bool = False) -> list[dict]:
    create_tables()

    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT c.id, c.name, EXISTS(
                SELECT 1 FROM jobs j WHERE j.company_id = c.id
            ) AS has_jobs
            FROM companies c
            WHERE c.tracked = TRUE
            ORDER BY c.name
        """)
        rows = cur.fetchall()

    results = []
    for company_id, name, has_jobs in rows:
        results.append({"id": company_id, "name": name, "tracking_working": has_jobs})

    if dry_run:
        for r in results:
            status = "OK" if r["tracking_working"] else "NO JOBS"
            logger.info(f"  {r['name']}: {status}")
        return results

    with _connect() as conn, conn.cursor() as cur:
        for r in results:
            cur.execute(
                "UPDATE companies SET tracking_working = %s WHERE id = %s",
                (r["tracking_working"], r["id"]),
            )
    logger.info(f"Updated tracking_working for {len(results)} tracked companies")

    return results


def send_alert(broken: list[dict]) -> None:
    if not GMAIL_APP_PASSWORD or not RECIPIENT_EMAIL:
        logger.warning("Gmail credentials not configured — skipping alert email")
        return

    today = datetime.now(timezone.utc).strftime("%b %d, %Y")
    names = "\n".join(f"  • {c['name']}" for c in broken)

    html = f"""\
<p>The following <strong>{len(broken)}</strong> tracked companies have <strong>zero jobs</strong> in the database as of {today}:</p>
<ul>
{"".join(f"<li>{c['name']}</li>" for c in broken)}
</ul>
<p>Check that the Google Alert for each company's career page is still active and producing results.</p>
<p style="color:#888;font-size:12px;">Sent by audit_tracking.py</p>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"⚠️ {len(broken)} company tracking alerts need attention — {today}"
    msg["From"] = RECIPIENT_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(RECIPIENT_EMAIL, GMAIL_APP_PASSWORD.replace(" ", ""))
        server.sendmail(RECIPIENT_EMAIL, RECIPIENT_EMAIL, msg.as_string())

    logger.info(f"Alert email sent to {RECIPIENT_EMAIL}")


def main():
    dry_run = "--dry-run" in sys.argv
    results = audit_tracking(dry_run=dry_run)

    broken = [r for r in results if not r["tracking_working"]]
    working = [r for r in results if r["tracking_working"]]

    logger.info(f"Summary: {len(working)} working, {len(broken)} broken out of {len(results)} tracked companies")

    if broken and not dry_run:
        send_alert(broken)
    elif not broken:
        logger.info("All tracked companies have jobs — no alert needed")


if __name__ == "__main__":
    main()
