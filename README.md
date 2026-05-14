# Job Search App

Email-based job search digest with semantic matching.

---

## To-Do

- [ ] **Adjust LinkedIn job alerts** — the script only indexes the 5–6 job previews shown in each alert email, not the full results. Set up more granular alerts (e.g. by role keyword per company) to maximize coverage.

- [ ] **Manually verify fetcher captures all Google Alert results** — spot-check alert emails vs. fetcher output over the next few days to confirm no results are being missed

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
