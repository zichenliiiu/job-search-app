# Job Search App

Email-based job search digest with AI-powered ranking and resume generation.

---

## Code Structure

### File map

```
fetch_jobs.py          Entry point — fetches Gmail alerts, enriches descriptions, saves to DB (no AI, runs hourly)
send_digest.py         Entry point — ranks all undigested jobs via Claude and sends the daily email digest
generate_resume.py     Entry point — generates a tailored resume for a specific job
api.py                 Flask API server — serves ranked jobs from Postgres to the frontend

src/
  job_class.py         Job dataclass — shared data model across all modules
  gmail_fetcher.py     Gmail API client — fetches unread emails, scrapes job descriptions
  parsers.py           Email HTML parsers + URL→company extractor — no network I/O
  database.py          Postgres layer — insert, query, and rank jobs; users/criteria/companies tables
  auth.py              Google OAuth login (Authlib) — session cookie auth, /api/auth/* routes
  ranker.py            Claude-powered scorer — returns tiered RankerResult
  email_digest.py      HTML email builder and Gmail SMTP sender
  resume_generator.py  Claude-powered resume tailor — selects and rewrites bullets for a role
  pdf_converter.py     HTML→PDF converter with automatic font scaling to enforce 1-page limit

config/
  resume.txt           Your resume (plain text) — read by ranker.py and resume_generator.py
  criteria.txt         What you're looking for — original source for the global ranker (see
                       "Authentication & Per-User Settings" — per-user criteria now lives in DB)
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

**send_digest.py** (runs once daily at midnight SF time via GitHub Actions)
```
1. database.fetch_undigested_jobs()     loads all jobs where digested_at IS NULL

2. ranker.rank_jobs(jobs)               sends the full undigested pool to Claude in one prompt,
                                        returns RankerResult with top / next_best tiers
   database.save_ranking(result, jobs)  writes tier / tier_order / reason / ranked_at
                                        back to each job row; marks below-threshold jobs 'skip'

3. email_digest.send_digest(result)     renders HTML digest, sends via Gmail SMTP
   database.mark_jobs_digested(hashes)  stamps digested_at=NOW() on sent jobs
```

Keeping fetch and rank separate ensures that `tier_order` is always globally consistent for the day's digest — the ranker always sees the full accumulated pool of undigested jobs in one shot, regardless of how many fetch runs have occurred.

### Data flow (api.py → frontend)

```
Browser → Vite dev server (localhost:5173)
            └─ /api/* proxied → Flask (localhost:5001)
                  └─ queries Postgres

GET /api/dates
      └─ SELECT DISTINCT DATE(ranked_at) FROM jobs WHERE tier IN ('top','next_best')
         Returns: [{ date, label, day }]  e.g. [{ date: "2026-05-28", label: "Today", day: "Thu · May 28" }]

GET /api/feed?date=YYYY-MM-DD
      └─ SELECT … FROM jobs WHERE tier IN ('top','next_best') AND DATE(ranked_at) = date
         Returns: { topPicks: [Job], nextBest: [Job], syncedAt: string }

DB column → frontend field mapping:
  title      → role
  company    → co
  location   → loc
  url_hash   → id   (used as stable React key and track toggle identifier)
  url        → url
  reason     → reason
  fetched_at → posted  (rendered as relative label: "Today", "1d ago", …)
  location   → remote  ("Remote OK" pill if "remote" appears in location, else null)
  tier_order → tierOrder
  salary     → null    (not stored in DB; field reserved for future enrichment)
```

> **Note:** `/api/dates` and `/api/feed` are not yet user-scoped — they still read the global
> `tier`/`tier_order`/`reason`/`ranked_at` columns on `jobs`, populated by the single global
> `send_digest.py` run (using `config/criteria.txt`). See "Authentication & Per-User Settings"
> below for what's been built so far toward making this per-user, and what's still outstanding.

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

**Status:** Settings UI (`SettingsPage.jsx`) reads/writes these tables and is live for user 1
(zichenliu9@gmail.com), seeded with their existing `config/criteria.txt` and all 54 companies
currently in the `jobs` table. However, `/api/dates` and `/api/feed` (and the
`send_digest.py`/`ranker.py` pipeline) do NOT yet consume `user_criteria` / `user_companies` —
they still operate on the single global `jobs.tier`/`tier_order`/`reason` columns produced by one
shared ranking run. Making the feed and digest per-user is the next phase (see To-Do).

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

- [ ] **Rewire `/api/dates` and `/api/feed` to per-user data** — filter by the logged-in user's `user_companies`, and score against their `user_criteria` instead of the single global `config/criteria.txt` run.

- [ ] **Per-user ranking & digest pipeline** — `send_digest.py`/`ranker.py` currently rank the global job pool once against `config/criteria.txt` and email `RECIPIENT_EMAIL`. Needs to become: for each user, rank their followed companies' jobs against their `user_criteria.criteria_text` and send to their own email.

- [ ] **Company name dedup** — `jobs.company` has near-duplicate values for the same company (e.g. `Openai`/`OpenAI`, `Google`/`Google DeepMind`, `Primeintellect`/`Prime Intellect`, `Sierra`/`Sierra Studio`, `Gleanwork`/`Glean`, `Metacareers`/`Meta`). Normalize in `parsers.py` so company-following matches reliably.

---

## Ranking Algorithm Design

### Inputs
- `config/resume.txt` — plain text resume
- `config/criteria.txt` — free-text description of what you're looking for (role, seniority, industry preferences, deal-breakers, etc.)
- All undigested jobs (fetched from Gmail but not yet surfaced in a digest), with title + company + description

### How it works
Each job is categorized by an LLM (Claude) in a single batched prompt. The prompt includes the resume, the criteria, and the job details, and asks the model to directly assign a tier and a one-line reason — `config/criteria.txt` describes what "top", "next best", and "skip" jobs look like, in the user's own words.

Jobs are then split into tiers and written back to the database:
- **Top** (`tier = 'top'`) — matches the "top" description in `config/criteria.txt`.
- **Next Best** (`tier = 'next_best'`) — matches the "next best" description in `config/criteria.txt`.
- **Skip** (`tier = 'skip'`) — matches the "skip" description. Stored but not surfaced in the digest or web app.

Each ranked job also gets `tier_order` (position within its tier, ordered by Claude from strongest to weakest match), `reason` (one-line Claude rationale), and `ranked_at` (timestamp of the ranking run). The web frontend uses these columns to display the day's feed.

### Digest behaviour
- If Top Options is non-empty: send both sections.
- If Top Options is empty: send only Next Best with a note that nothing cleared the bar today.
- If both are empty: skip sending (or send a brief "nothing new" note — TBD).

### Files
- `config/resume.txt` — user-maintained
- `config/criteria.txt` — user-maintained
- `src/ranker.py` — calls Claude API, returns scored + tiered job list ✅
- `src/database.py` — `save_ranking()` persists tier/tier_order/reason/ranked_at ✅
- `src/email_digest.py` — renders tiered results into HTML and sends via Gmail SMTP ✅
- `api.py` — Flask API serving ranked jobs from Postgres to the frontend ✅
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
