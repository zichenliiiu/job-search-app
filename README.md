# Job Search App

Email-based job search digest with AI-powered ranking and resume generation.

---

## Code Structure

### File map

```
fetch_jobs.py          Entry point — fetches Gmail alerts, enriches descriptions, saves to DB (no AI, runs hourly)
send_digest.py         Entry point — for each user, ranks their unranked jobs via Claude and emails their digest
generate_resume.py     Entry point — generates a tailored resume for a specific job
api.py                 Flask API server — serves each user's ranked jobs from Postgres to the frontend

src/
  job_class.py         Job dataclass — shared data model across all modules
  gmail_fetcher.py     Gmail API client — fetches unread emails, scrapes job descriptions
  parsers.py           Email HTML parsers + URL→company extractor — no network I/O
  database.py          Postgres layer — insert/query jobs; users/criteria/companies/rankings tables
  auth.py              Google OAuth login (Authlib) — session cookie auth, /api/auth/* routes
  ranker.py            Claude-powered scorer — returns tiered RankerResult for a given criteria text
  email_digest.py      HTML email builder and Gmail SMTP sender
  resume_generator.py  Claude-powered resume tailor — selects and rewrites bullets for a role
  pdf_converter.py     HTML→PDF converter with automatic font scaling to enforce 1-page limit

config/
  resume.txt           Resume (plain text) — read by ranker.py and resume_generator.py for all users
  criteria.txt         Legacy — original source for the global ranker, now only used as a fallback
                       default in eval/eval.py. Per-user criteria lives in the user_criteria table.
  job_description.txt  Job description to tailor resume against — read by resume_generator.py
  resume_prompt.txt    Prompt instructions for resume tailoring — edit to iterate on behavior

frontend/              React web app (Vite) — displays ranked openings
  src/
    App.jsx            Top-level shell; auth check, then fetches dates/feed; switches feed/settings views
    components/        TopBar, PageHeader, SummaryRow, Section, JobCard, LoginPage, SettingsPage
    styles/            tokens.css (design tokens), app.css (view styles)
  public/favicon.svg
  index.html / vite.config.js / package.json
```

### Data flow

The pipeline is split into two independent scripts with different cadences:

**fetch_jobs.py** (runs hourly via GitHub Actions — no AI cost)
```
1. GmailFetcher.fetch_all_jobs()
      ├─ reads unread LinkedIn + Google Alert emails via Gmail API
      └─ calls parsers.parse_linkedin_email / parse_google_alert_email → list[Job]

2. GmailFetcher.enrich_with_descriptions(jobs)
      ├─ scrapes each job URL for the full posting text
      └─ calls parsers.extract_ats_description to extract clean text

3. database.insert_jobs(jobs)           writes to Postgres, deduplicates by url_hash
```

**send_digest.py** (runs once daily at midnight SF time via GitHub Actions, loops over all users)
```
For each user:
  1. database.get_followed_companies(user_id) / get_user_criteria(user_id)
        skip the user if they follow no companies or have no criteria set

  2. database.get_unranked_jobs_for_user(user_id)
        jobs from their followed companies with no row yet in user_job_rankings for this user

  3. ranker.rank_jobs(jobs, criteria_text)   sends that user's unranked jobs to Claude in one prompt,
                                              returns RankerResult with top / next_best tiers
     database.save_user_ranking(user_id, result, jobs)
        writes (user_id, job_id, tier, tier_order, reason, ranked_at) to user_job_rankings;
        jobs not in top/next_best are recorded as tier='skip' so they're never re-ranked for this user

  4. email_digest.send_digest(result, recipient_email=user_email)
        renders HTML digest, sends via Gmail SMTP to the user's own email
```

Keeping fetch and rank separate ensures `tier_order` is consistent within each user's daily batch — the ranker sees that user's full accumulated pool of unranked jobs in one shot, regardless of how many fetch runs have occurred. Because ranking is per-user, the same job can end up in different tiers (or be ranked at different times) for different users.

### Data flow (api.py → frontend)

```
Browser → Vite dev server (localhost:5173)
            └─ /api/* proxied → Flask (localhost:5001)
                  └─ queries Postgres

GET /api/dates   (login required)
      └─ SELECT DISTINCT DATE(ranked_at) FROM user_job_rankings
         WHERE user_id = <current user> AND tier IN ('top','next_best')
         Returns: [{ date, label, day }]  e.g. [{ date: "2026-05-28", label: "Today", day: "Thu · May 28" }]

GET /api/feed?date=YYYY-MM-DD   (login required)
      └─ SELECT … FROM user_job_rankings JOIN jobs ON job_id = jobs.id
         WHERE user_id = <current user> AND tier IN ('top','next_best') AND DATE(ranked_at) = date
         Returns: { topPicks: [Job], nextBest: [Job], syncedAt: string }

DB column → frontend field mapping:
  title      → role
  company    → co
  location   → loc
  url_hash   → id   (used as stable React key and track toggle identifier)
  url        → url
  reason     → reason          (from user_job_rankings)
  fetched_at → posted  (rendered as relative label: "Today", "1d ago", …)
  location   → remote  ("Remote OK" pill if "remote" appears in location, else null)
  tier_order → tierOrder       (from user_job_rankings)
  salary     → null    (not stored in DB; field reserved for future enrichment)
```

### Authentication & Per-User Settings

Login is handled via Google OAuth (Authlib), with Flask session cookies. Vercel rewrites `/api/*`
to the Railway backend, so the frontend and API are same-origin and cookies work without CORS.

```
users
  id, provider, provider_sub, email, name, created_at
  — one row per (provider, provider_sub), created on first login

user_criteria
  user_id (PK, FK → users), criteria_text
  — free-text ranking criteria, replaces config/criteria.txt on a per-user basis

user_companies
  user_id (FK → users), company
  — companies the user follows; PK is (user_id, company)

user_job_rankings
  user_id (FK → users), job_id (FK → jobs), tier, tier_order, reason, ranked_at
  — PK is (user_id, job_id); one row per (user, job) once that job has been ranked
    ('top' / 'next_best' / 'skip') for that user. The same job can have different
    rows (different tier/reason) for different users.
```

Auth routes (`src/auth.py`, mounted at `/api/auth`):
```
GET  /api/auth/login/google      redirect to Google's OAuth consent screen
GET  /api/auth/callback/google   exchange code, get_or_create_user(), set session, redirect to /
POST /api/auth/logout            clear session
GET  /api/auth/me                return {id, email, name, ...} or 401 if not logged in
```

Settings routes (`api.py`, all `@login_required`):
```
GET  /api/criteria     → { criteria_text }
PUT  /api/criteria     ← { criteria_text }                 upserts user_criteria

GET  /api/companies    → { all: [company...], followed: [company...] }
                          "all" = get_distinct_companies() from jobs table
PUT  /api/companies    ← { companies: [company...] }       replaces user_companies
```

**Status:** Settings UI (`SettingsPage.jsx`) reads/writes `user_criteria`/`user_companies` and is
live for user 1 (zichenliu9@gmail.com). `/api/dates` and `/api/feed` now read from
`user_job_rankings`, and `send_digest.py`/`ranker.py` rank each user's unranked jobs against
their own `user_criteria.criteria_text` and email their own `users.email`. The old global
`jobs.tier`/`tier_order`/`reason`/`ranked_at`/`digested_at` columns have been removed — for user 1,
their existing rankings (1,120 jobs) were migrated into `user_job_rankings` as a one-time backfill.

### Data flow (generate_resume.py)

```
1. Load config/resume.txt, config/job_description.txt, config/resume_prompt.txt

2. resume_generator._call_claude()
      ├─ sends resume + job description to Claude (claude-opus-4-7)
      ├─ Claude selects relevant bullets, rewrites wording to mirror JD language
      └─ returns structured JSON: { header, experiences[], education }

3. resume_generator._build_html()
      └─ injects JSON content into a fixed HTML template → output/resume_<ts>.html

4. pdf_converter.convert_to_pdf()
      ├─ renders HTML with weasyprint, checks page count
      ├─ if > 1 page: reduces font size (10.5pt → 10pt → 9.5pt → 9pt) and re-renders
      └─ writes final one-page PDF → output/resume_<ts>.pdf
```

---

## Running the web app

Two processes must be running in parallel:

```bash
# Terminal 1 — API server (port 5001)
source venv/bin/activate && python api.py

# Terminal 2 — Vite dev server (port 5173)
cd frontend && npm run dev
```

Then open `http://localhost:5173`. Vite proxies all `/api/*` requests to Flask, so no CORS configuration is needed.

The date scrubber in the top bar shows only dates for which ranked jobs exist in the database. If the database is empty the feed shows blank sections.

---

## To-Do

- [ ] **Adjust LinkedIn job alerts** — the script only indexes the 5–6 job previews shown in each alert email, not the full results. Set up more granular alerts (e.g. by role keyword per company) to maximize coverage.

- [ ] **Manually verify fetcher captures all Google Alert results** — 5/15 update: changed google alert to as-it-happens vs. digest emails, since digest emails cap the results at 3. Updated fetcher but since there is no alert email to test yet, double check this again when there is real alert emails.

- [ ] **Fine-tune ranking prompt** — iterate on `config/criteria.txt` and the system prompt in `src/ranker.py` based on `eval/eval.py` results.

- [ ] **Fine-tune resume generation prompt** — iterate on `config/resume_prompt.txt` based on output quality; focus on bullet selection relevance, wording match to JD, and length discipline. The prompt file is intentionally separate so it can be edited without touching code.

- [ ] **Rank the user-1 backlog** — 1,211 jobs predate the per-user pipeline and were never ranked under the old system either (`tier IS NULL`). They'll be picked up by the next `send_digest.py` run as "unranked for user 1" — this first run will be a larger-than-usual Claude batch (likely hits the token-budget truncation fallback in `ranker.py`). Consider bulk-marking them `skip` in `user_job_rankings` first if that's not desired.

- [ ] **Company name dedup** — `jobs.company` has near-duplicate values for the same company (e.g. `Openai`/`OpenAI`, `Google`/`Google DeepMind`, `Primeintellect`/`Prime Intellect`, `Sierra`/`Sierra Studio`, `Gleanwork`/`Glean`, `Metacareers`/`Meta`). Normalize in `parsers.py` so company-following matches reliably.

---

## Ranking Algorithm Design

### Inputs (per user)
- `config/resume.txt` — resume (shared across users for now)
- `user_criteria.criteria_text` — free-text description of what that user is looking for (role, seniority, industry preferences, deal-breakers, etc.)
- That user's unranked jobs — jobs from companies in their `user_companies` with no row yet in `user_job_rankings` for them, with title + company + description

### How it works
For each user, their unranked jobs are categorized by an LLM (Claude) in a single batched prompt. The prompt includes the resume, that user's `criteria_text`, and the job details, and asks the model to directly assign a tier and a one-line reason — the criteria text describes what "top", "next best", and "skip" jobs look like, in the user's own words.

Jobs are then split into tiers and written to `user_job_rankings`:
- **Top** (`tier = 'top'`) — matches the "top" description in the user's criteria.
- **Next Best** (`tier = 'next_best'`) — matches the "next best" description.
- **Skip** (`tier = 'skip'`) — matches the "skip" description. Stored so the job is never re-ranked for this user, but not surfaced in the digest or web app.

Each ranked row also gets `tier_order` (position within its tier, ordered by Claude from strongest to weakest match), `reason` (one-line Claude rationale), and `ranked_at` (timestamp of the ranking run). The web frontend uses these columns to display the day's feed for the logged-in user.

### Digest behaviour
- If Top Options is non-empty: send both sections.
- If Top Options is empty: send only Next Best with a note that nothing cleared the bar today.
- If both are empty: skip sending (or send a brief "nothing new" note — TBD).

### Files
- `config/resume.txt` — user-maintained
- `user_criteria` table — per-user, edited via the Settings page
- `src/ranker.py` — calls Claude API with a given criteria text, returns scored + tiered job list ✅
- `src/database.py` — `save_user_ranking()` persists rows to `user_job_rankings` ✅
- `src/email_digest.py` — renders tiered results into HTML, sends via Gmail SMTP to a given recipient ✅
- `api.py` — Flask API serving each user's ranked jobs from Postgres to the frontend ✅
- `frontend/` — React app displaying the ranked feed ✅

---

## Resume Generation Design

### Inputs
- `config/resume.txt` — plain text resume (same file used by ranker)
- `config/job_description.txt` — the specific job posting to tailor against
- `config/resume_prompt.txt` — prompt instructions controlling selection and wording behavior; edit this file to iterate without touching code

### How it works
Claude receives the full resume and job description, and is instructed to:
1. **Select** the most relevant experiences — up to 3 jobs, up to 4 bullets each; irrelevant bullets and jobs are dropped
2. **Rewrite** bullet wording to mirror terminology from the job description, without fabricating or exaggerating
3. **Preserve** the header (name/contact) and education section verbatim
4. **Return structured JSON** — `{ header, experiences[], education }` — so the HTML template stays stable and only content changes between runs

The HTML template is a fixed Python function (`_build_html`) that injects the JSON into a consistent layout. Claude never touches the styling.

The PDF converter enforces a one-page letter-size output by scaling font size down (10.5pt → 9pt) if content overflows, using weasyprint's render API to check page count before writing.

### Usage
```bash
# Paste a job description into config/job_description.txt, then:
python generate_resume.py

# Outputs both:
#   output/resume_<timestamp>.html   (preview in browser)
#   output/resume_<timestamp>.pdf    (submit to ATS)
```

### Files
- `config/resume.txt` — user-maintained
- `config/job_description.txt` — user-maintained (swap in each new role)
- `config/resume_prompt.txt` — user-maintained (iterate on selection/wording behavior)
- `src/resume_generator.py` — Claude API call + HTML builder ✅
- `src/pdf_converter.py` — weasyprint conversion with font scaling ✅
- `generate_resume.py` — CLI entry point ✅
