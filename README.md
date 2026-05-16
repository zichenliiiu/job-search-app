# Job Search App

Email-based job search digest with AI-powered ranking and resume generation.

---

## Code Structure

### File map

```
run_digest.py          Entry point — orchestrates the full daily pipeline
generate_resume.py     Entry point — generates a tailored resume for a specific job
test_fetch.py          Manual test runner for fetching and inspecting jobs

src/
  job_class.py         Job dataclass — shared data model across all modules
  gmail_fetcher.py     Gmail API client — fetches unread emails, scrapes job descriptions
  parsers.py           Email HTML parsers + URL→company extractor — no network I/O
  database.py          Postgres layer — insert and query jobs
  ranker.py            Claude-powered scorer — returns tiered RankerResult
  email_digest.py      HTML email builder and Gmail SMTP sender
  resume_generator.py  Claude-powered resume tailor — selects and rewrites bullets for a role
  pdf_converter.py     HTML→PDF converter with automatic font scaling to enforce 1-page limit

config/
  resume.txt           Your resume (plain text) — read by ranker.py and resume_generator.py
  criteria.txt         What you're looking for — read by ranker.py at runtime
  job_description.txt  Job description to tailor resume against — read by resume_generator.py
  resume_prompt.txt    Prompt instructions for resume tailoring — edit to iterate on behavior
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

## To-Do

- [ ] **Adjust LinkedIn job alerts** — the script only indexes the 5–6 job previews shown in each alert email, not the full results. Set up more granular alerts (e.g. by role keyword per company) to maximize coverage.

- [ ] **Manually verify fetcher captures all Google Alert results** — 5/15 update: changed google alert to as-it-happens vs. digest emails, since digest emails cap the results at 3. Updated fetcher but since there is no alert email to test yet, double check this again when there is real alert emails.

- [ ] **Fine-tune ranking prompt** — iterate on `config/criteria.txt` and the system prompt in `src/ranker.py` based on results; check whether top/next-best thresholds (75/40) need adjusting.

- [ ] **Fine-tune resume generation prompt** — iterate on `config/resume_prompt.txt` based on output quality; focus on bullet selection relevance, wording match to JD, and length discipline. The prompt file is intentionally separate so it can be edited without touching code.

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
