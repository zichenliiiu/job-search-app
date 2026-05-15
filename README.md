# Job Search App

Email-based job search digest with semantic matching.

---

## Code Structure

### File map

```
run_digest.py        Entry point — orchestrates the full daily pipeline
test_fetch.py        Manual test runner for fetching and inspecting jobs

src/
  job_class.py       Job dataclass — shared data model across all modules
  gmail_fetcher.py   Gmail API client — fetches unread emails, scrapes job descriptions
  parsers.py         Email HTML parsers + URL→company extractor — no network I/O
  database.py        Postgres layer — insert and query jobs
  ranker.py          Claude-powered scorer — returns tiered RankerResult
  email_digest.py    HTML email builder and Gmail SMTP sender

config/
  resume.txt         Your resume (plain text) — read by ranker.py at runtime
  criteria.txt       What you're looking for — read by ranker.py at runtime
```

### Data flow (run_digest.py)

```
1. GmailFetcher.fetch_all_jobs()
      ├─ reads unread LinkedIn + Google Alert emails via Gmail API
      └─ calls parsers.parse_linkedin_email / parse_google_alert_email → list[Job]

2. GmailFetcher.enrich_with_descriptions(jobs)
      ├─ scrapes each job URL for the full posting text
      └─ calls parsers.extract_ats_description to extract clean text

3. database.insert_jobs(jobs)         writes to Postgres, deduplicates by url_hash
   database.fetch_recent_jobs(24h)    reads back jobs for ranking

4. ranker.rank_jobs(jobs)             sends all jobs to Claude in one prompt,
                                      returns RankerResult with top / next_best tiers

5. email_digest.send_digest(result)   renders HTML digest, sends via Gmail SMTP
```

---

## To-Do

- [ ] **Adjust LinkedIn job alerts** — the script only indexes the 5–6 job previews shown in each alert email, not the full results. Set up more granular alerts (e.g. by role keyword per company) to maximize coverage.

- [ ] **Manually verify fetcher captures all Google Alert results** — 5/15 update: changed google alert to as-it-happens vs. digest emails, since digest emails cap the results at 3. Updated fetcher but since there is no alert email to test yet, double check this again when there is real alert emails

- [ ] **Fine-tune ranking prompt** — iterate on `config/criteria.txt` and the system prompt in `src/ranker.py` based on results; check whether top/next-best thresholds (75/40) need adjusting

---

## Ranking Algorithm Design

### Inputs
- `config/resume.txt` — plain text resume
- `config/criteria.txt` — free-text description of what you're looking for (role, seniority, industry preferences, deal-breakers, etc.)
- Jobs fetched in the last 24h, with title + company + description

### How it works
Each job is scored by an LLM (Claude) in a single batched prompt. The prompt includes the resume, the criteria, and the job details, and asks the model to return a score (0–100) and a one-line reason.

Jobs are then split into two tiers:
- **Top Options** — score ≥ threshold (e.g. 75). Strong match on role fit, seniority, and stated preferences.
- **Next Best** — score below threshold but above a floor (e.g. 40). Partial matches worth a quick look on thin days.
- Jobs below the floor are dropped silently.

### Digest behaviour
- If Top Options is non-empty: send both sections.
- If Top Options is empty: send only Next Best with a note that nothing cleared the bar today.
- If both are empty: skip sending (or send a brief "nothing new" note — TBD).

### Files
- `config/resume.txt` — user-maintained
- `config/criteria.txt` — user-maintained
- `src/ranker.py` — calls Claude API, returns scored + tiered job list ✅
- `src/email_digest.py` — renders tiered results into HTML and sends via Gmail SMTP ✅
