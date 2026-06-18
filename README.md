# Job Search Digest

Job search with a filter, not a firehose. Follow the companies you care about, describe the role you want in plain English, and get a daily digest with only what clears the bar — no noise, no manual sourcing.

---

## Features

- **Per-user settings** — each user sets their own ranking criteria (free text) and followed companies via a settings page
- **Feed** — daily view of highlighted openings;
- **Email digest** — ranked HTML email delivered each morning

---

## Decisions & Tradeoffs

_Product decisions_
- **Company list is user-provided, not generated in app** — building a target company list is a thinking exercise best done in a chat interface; Prompt users to bring the curated list, no reason to rebuild ChatGPT inside this app.

_Technical architecture_
- **Fetch, rank, and serve are fully decoupled** — each stage writes to Postgres before handing off, so a failure in any one doesn't cascade. Ranking picks up exactly where it left off; nothing is reprocessed or lost.

_Growth / experimentation_
- **Subject line is Claude-generated fresh each morning** — avoids the "same sender, same subject" inbox blindness that kills open rates on recurring digests.

_Prompt design_
- **User description of target role beats resume signal** — the ranker uses what the user says they want, not what their resume suggests. A resume reflects the past; the criteria text reflects the goal.

---

## Architecture

Five pipeline stages, deliberately decoupled:

**1. Source**
Google Alerts monitor each target company's careers site directly — when a new opening page gets indexed, an alert email arrives to a monitored inbox. This keeps the signal close to the source (the company's own postings) rather than relying on aggregators that may lag, truncate, or reformat listings.

**2. Fetch (hourly, no AI cost)**
Gmail API reads unread job alert emails → scrapes full posting text from each URL → writes to Postgres. Keeping this stage AI-free means it can run frequently without accumulating Claude API costs.

**3. Rank (once daily per user, batched)**
For each user: pull all unranked jobs from their followed companies → send them to Claude in a single prompt alongside the user's free-text criteria → receive back a tiered list (`top` / `next_best` / `skip`) with a one-line reason per job. 

**4. Serve**
React frontend with Flask API reading each user's ranked jobs, hosted on Vercel. 

**5. Digest**
A python script that runs daily, sends ranked jobs to user's email, hosted on Github Actions. 

---

## Stack

Python (Flask, Authlib) · PostgreSQL · Claude API (claude-sonnet-4-6) · React + Vite · GitHub Actions · Deployed on Railway (API) + Vercel (frontend) + Supabase (DB)

---

## What I'd Build Next

- **Onboarding** — the app suffers from a cold start: an empty feed with no guidance. Lower the barrier with prefilled placeholder settings, example company watchlists, and guided prompts to help new users define their target role description before their first digest arrives.
- **Application tracking** — bookmarks and a lightweight status board (Applied → Phone screen → Onsite → Offer) for warm users who are actively managing a pipeline; right now that lives outside the app in Notion.
- **Ranking feedback** — thumbs up/down on recommended roles to tighten the ranker over time; right now criteria can only be improved by manually editing the settings text.

