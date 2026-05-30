# Job Search Automation System - PRD

## Overview
A personalized job search system that daily scrapes target company career pages, semantically ranks opportunities against your background, and auto-generates tailored resumes for top matches.

---

## Goals
- **MVP: Daily email digest** of new job openings from Tier 1 & 2 companies (via Gmail alerts)
- **Semantic relevance ranking** (not just keyword matching)
- **Test core functionality** before building full webapp
- **Future: Auto-generated resumes** and web UI for application management

---

## Tech Stack

### MVP (Email-Based System)
- **Language:** Python
- **Job Source:** Gmail API (LinkedIn alerts + Google alerts)
- **Email Parsing:** BeautifulSoup (HTML parsing)
- **APIs:** OpenAI (embeddings), Anthropic Claude (scoring)
- **Database:** PostgreSQL with pgvector extension (Supabase free tier)
- **Email Delivery:** SendGrid or AWS SES (for sending daily digest)
- **Automation:** GitHub Actions (daily cron job)

### Future: Full Web Application
- **Framework:** Next.js (React)
- **Hosting:** Vercel (free tier)
- **Additional features:** Resume generation, application tracking, profile management

---

## Data Sources: 3-Tiered Approach

### Tier 1: Top 20 Companies (LinkedIn Job Alerts via Gmail)
**Source:** LinkedIn job alert emails sent to Gmail daily

**Implementation:**
- Gmail API reads unread emails from `jobalerts-noreply@linkedin.com`
- Parse HTML email content to extract:
  - Job title
  - Company name
  - Location
  - Job URL
- Store jobs in database, dedupe by URL
- Mark emails as read after processing

**Advantages:**
- Reliable daily delivery
- No scraping needed
- LinkedIn's job index
- Works immediately (alerts already set up)

**Limitations:**
- Daily cadence (not real-time)
- Limited to LinkedIn's coverage
- Email format changes require parser updates

---

### Tier 2: Remaining ~50 Companies (Google Alerts via Gmail)
**Source:** Google Alert emails when new pages are indexed on company career sites

**Implementation:**
- Gmail API reads Google Alert emails
- Parse email to extract:
  - Alert snippet/summary
  - Link to new career page
- Optionally: Follow link and scrape full job description
- Store and score jobs

**Advantages:**
- Covers companies with poor LinkedIn presence
- Monitors career sites directly
- Free

**Limitations:**
- Google indexing lag (not immediate)
- Alert quality varies
- May include non-job pages

---

### Tier 3: Manual LinkedIn Browse (Placeholder)
**Source:** LinkedIn job board daily manual review

**Current approach (MVP):**
- Daily manual check of LinkedIn's algorithmic recommendations
- Copy/paste or bookmark interesting roles
- This tier is intentionally manual for now

**Future iteration options:**
- Browser extension to capture jobs you view
- LinkedIn saved jobs API integration
- Automated LinkedIn search scraping (higher risk)

**Note:** This tier is a placeholder to be refined based on what works in Tier 1 & 2.

---

## Core Components (MVP)

### 1. Gmail Job Fetcher
**Purpose:** Collect job postings from Gmail (LinkedIn alerts + Google alerts)

**Key Features:**
- Gmail API integration with OAuth
- Filter emails by sender (`jobalerts-noreply@linkedin.com`, Google Alerts)
- Parse HTML email content (BeautifulSoup)
- Extract: job title, company, location, URL
- Dedupe by URL hash
- Mark emails as read after processing

---

### 2. Semantic Matcher
**Purpose:** Score jobs against your background using semantic similarity + LLM reasoning

**Key Features:**
- Profile stored as markdown (background, experiences, skills, preferences)
- Vector similarity for fast filtering (OpenAI embeddings)
- LLM-based scoring with explanation (Claude: 0-100 score + 2-3 sentence reasoning)
- Store scores in database

---

### 3. Daily Email Digest Generator
**Purpose:** Send ranked job recommendations via email every morning

**Key Features:**
- Query database for new jobs from past 24 hours
- Sort by relevance score (highest first)
- Generate HTML email with:
  - Job title, company, score
  - Match explanation
  - Link to job posting
- Group by tier (Tier 1: LinkedIn alerts, Tier 2: Google alerts)
- Send via SendGrid/AWS SES

**Email Format:**
```
Subject: Daily Job Digest - 8 New Matches

--- TIER 1: TOP COMPANIES (LinkedIn) ---

⭐ 95 | Senior Product Strategist - Figma
Strong match: Your design tools PM experience aligns perfectly...
[View Job] https://linkedin.com/jobs/...

⭐ 87 | Strategy & Ops Lead - Stripe
Good fit: Your fintech background matches 3 of 4 requirements...
[View Job] https://linkedin.com/jobs/...

--- TIER 2: TRACKED COMPANIES (Google Alerts) ---

⭐ 82 | Product Strategy Manager - Notion
Decent match: Strong on strategy, light on B2B SaaS...
[View Job] https://notion.so/careers/...

...
```

---

## MVP Workflow

The pipeline runs as two separate GitHub Actions workflows:

**Hourly — fetch_jobs.py:**
1. Fetch unread LinkedIn job alert emails
2. Fetch unread Google Alert emails
3. Parse and extract job data
4. Check for duplicates (URL hash)
5. Store new jobs in database
6. Mark source emails as read

**Daily at midnight SF time — send_digest.py:**
1. Load all undigested jobs from database
2. Score all jobs in one batched Claude API call
3. Generate HTML email digest
4. Send email to inbox
5. Mark jobs as digested

Separating fetch from rank ensures the daily digest always ranks the full accumulated pool of undigested jobs in one global pass — no duplicate tier ordering across multiple fetch runs.

---

## Future: Web Application

Once MVP email digest is validated, build full web interface:

### Additional Components

**Resume Generator:**
- Master experiences repository (JSON with all bullets tagged)
- Claude selects 8-12 most relevant bullets per job
- LaTeX or python-docx template rendering
- PDF output

**Web Pages:**
- `/` - Daily digest (top matches sorted by score)
- `/job/[id]` - Job detail + match explanation + resume preview
- `/profile` - Edit background and experiences
- `/companies` - Manage company list and alert settings
- `/applied` - Application tracking

**Tech Stack Additions:**
- FastAPI backend
- Next.js frontend
- Deployed on Railway + Vercel

---

## Research Notes: Available AI Job Search Tools

### Tools Tested

#### JobRight

**Issues Found:**
- **Too spammy:** High volume of irrelevant recommendations
- **High error rate:** Many openings don't fit background or target company profile
- **Poor matching quality:** Recommendations don't align with product strategy focus or company preferences

---

#### Sonara

**Issues Found:**
- **Auto-application focused:** Primary feature is automated submission without review
- **Spammy job matches:** Recommendations are low-quality, not relevant to product strategy
- **No manual review workflow:** Cannot see list of openings before they're submitted
- **No resume control:** Cannot review or iterate on resume before applications go out
- **Spray and pray approach:** High-volume, low-quality strategy

---

#### [Other Tools]
*Add notes as you test more tools...*

---

*Last updated: May 13, 2026*
*Status: PRD / Research Phase*
