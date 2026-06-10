"""Flask API server — serves ranked jobs from the database to the frontend."""

from datetime import date, datetime, timezone, timedelta
from flask import Flask, jsonify, request
import psycopg2
import psycopg2.extras
from config.config import DATABASE_URL, FLASK_SECRET_KEY, APP_BASE_URL
from src.auth import init_auth, login_required, current_user_id
from src.database import (
    create_tables,
    get_user_criteria,
    save_user_criteria,
    get_followed_companies,
    set_followed_companies,
    get_all_companies,
)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = APP_BASE_URL.startswith('https')

create_tables()
init_auth(app)


def _connect():
    return psycopg2.connect(DATABASE_URL)


def _relative_label(d):
    today = datetime.now(timezone.utc).date()
    delta = (today - d).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Yesterday"
    return f"{delta}d ago"


def _format_day(d):
    return d.strftime("%a · %b %-d")


def _remote_label(location):
    if not location:
        return None
    low = location.lower()
    if "remote" in low:
        return "Remote OK"
    return None


def _job_row_to_dict(row) -> dict:
    url_hash, title, company, location, url, reason, tier_order = row
    return {
        "id": url_hash,
        "role": title or "",
        "co": company or "",
        "loc": location or "",
        "remote": _remote_label(location),
        "url": url,
        "reason": reason or "",
        "tierOrder": tier_order,
    }


@app.route("/api/dates")
@login_required
def get_dates():
    """Return distinct dates (newest first) when this user's jobs were ranked."""
    sql = """
        SELECT DISTINCT DATE(ranked_at AT TIME ZONE 'UTC') AS d
        FROM user_job_rankings
        WHERE user_id = %s AND tier IN ('top', 'next_best')
        ORDER BY d DESC
        LIMIT 30
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (current_user_id(),))
        rows = cur.fetchall()

    dates = []
    for (d,) in rows:
        dates.append({
            "date": d.isoformat(),
            "label": _relative_label(d),
            "day": _format_day(d),
        })

    return jsonify(dates)


@app.route("/api/feed")
@login_required
def get_feed():
    """Return this user's top and next_best jobs for the given date (YYYY-MM-DD)."""
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "date parameter required"}), 400

    sql = """
        SELECT j.url_hash, j.title, c.name, j.location, j.url, ujr.reason, ujr.ranked_at, ujr.tier_order, ujr.tier
        FROM user_job_rankings ujr
        JOIN jobs j ON j.id = ujr.job_id
        LEFT JOIN companies c ON c.id = j.company_id
        WHERE ujr.user_id = %s AND ujr.tier IN ('top', 'next_best')
          AND DATE(ujr.ranked_at AT TIME ZONE 'UTC') = %s
        ORDER BY ujr.tier, ujr.tier_order ASC
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (current_user_id(), date_str))
        rows = cur.fetchall()

    top_picks = []
    next_best = []
    synced_at = None

    for row in rows:
        url_hash, title, company, location, url, reason, ranked_at, tier_order, tier = row
        if synced_at is None and ranked_at is not None:
            synced_at = ranked_at.astimezone(timezone.utc).strftime("Last synced %-I:%M %p UTC")
        job = _job_row_to_dict(
            (url_hash, title, company, location, url, reason, tier_order)
        )
        if tier == "top":
            top_picks.append(job)
        else:
            next_best.append(job)

    return jsonify({
        "topPicks": top_picks,
        "nextBest": next_best,
        "syncedAt": synced_at or "",
    })

@app.route("/api/criteria", methods=["GET"])
@login_required
def get_criteria():
    return jsonify(get_user_criteria(current_user_id()))


@app.route("/api/criteria", methods=["PUT"])
@login_required
def put_criteria():
    data = request.get_json(force=True) or {}
    save_user_criteria(current_user_id(), criteria_text=data.get("criteria_text", ""))
    return jsonify({"ok": True})


@app.route("/api/companies", methods=["GET"])
@login_required
def get_companies():
    """Return the companies the user follows, plus which of those are not yet tracked."""
    all_companies = get_all_companies()
    tracked = {c["name"] for c in all_companies if c["tracked"]}
    untracked = {c["name"] for c in all_companies if not c["tracked"]}
    followed = get_followed_companies(current_user_id())
    return jsonify({
        "followed": followed,
        "untracked": [c for c in followed if c in untracked],
        "tracked": sorted(tracked),
    })


@app.route("/api/companies", methods=["PUT"])
@login_required
def put_companies():
    data = request.get_json(force=True) or {}
    companies = data.get("companies", [])
    set_followed_companies(current_user_id(), companies)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(port=5001, debug=True)
