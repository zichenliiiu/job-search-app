# Claude-powered job ranker.
# Called by run_digest.py after fetching recent jobs from the database.
#
#   rank_jobs(jobs)   sends all jobs to Claude in a single batched prompt,
#                     categorizes each against config/resume.txt + config/criteria.txt,
#                     and returns a RankerResult with two tiers:
#                       .top       — matches the "top" description in criteria.txt
#                       .next_best — matches the "next best" description in criteria.txt
#                     (jobs matching "skip" are dropped)

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import anthropic

from config.config import ANTHROPIC_API_KEY
from src.job_class import Job

logger = logging.getLogger(__name__)

DEFAULT_DESC_CAP = 1500
TOKEN_BUDGET = 190_000
MODEL = "claude-opus-4-7"


@dataclass
class RankedJob:
    job: Job
    reason: str
    tier: str  # 'top' or 'next_best'


@dataclass
class RankerResult:
    top: list[RankedJob]
    next_best: list[RankedJob]


def _load_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Required file not found: {path} — please create it.")
    return p.read_text(encoding='utf-8').strip()


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _build_job_block(index: int, job: Job, desc_cap: int) -> str:
    description = (job.description or job.raw_snippet or '')[:desc_cap]
    header = f"[{index}] {job.title} at {job.company}"
    if job.location:
        header += f" ({job.location})"
    return f"{header}\n{description}" if description else header


def rank_jobs(jobs: list[Job]) -> RankerResult:
    if not jobs:
        return RankerResult(top=[], next_best=[])

    resume = _load_text('config/resume.txt')
    criteria = _load_text('config/criteria.txt')

    desc_cap = DEFAULT_DESC_CAP
    job_blocks = [_build_job_block(i, j, desc_cap) for i, j in enumerate(jobs)]
    jobs_text = "\n\n".join(job_blocks)

    fixed_tokens = _estimate_tokens(resume) + _estimate_tokens(criteria) + 800
    total_tokens = fixed_tokens + _estimate_tokens(jobs_text)

    if total_tokens > TOKEN_BUDGET:
        for reduced_cap in [1000, 600, 300, 150]:
            job_blocks = [_build_job_block(i, j, reduced_cap) for i, j in enumerate(jobs)]
            jobs_text = "\n\n".join(job_blocks)
            total_tokens = fixed_tokens + _estimate_tokens(jobs_text)
            if total_tokens <= TOKEN_BUDGET:
                logger.warning(
                    f"Batch too large (~{total_tokens:,} estimated tokens, {len(jobs)} jobs): "
                    f"auto-truncated descriptions from {DEFAULT_DESC_CAP} to {reduced_cap} chars to fit within limit"
                )
                break
        else:
            logger.warning(
                f"Could not fit all {len(jobs)} jobs within {TOKEN_BUDGET:,} token budget even at "
                f"minimum description length (~{total_tokens:,} estimated tokens). Results may be incomplete."
            )

    system_prompt = f"""You are evaluating job postings for an user. Categorize each job posting based on the user's criteria.

## How the user describe criteria for each category
{criteria}
"""

    user_prompt = f"""Categorize the jobs below. Return ONLY a JSON array — no prose, no markdown fences.

Each element must have:
- "index": the job's [N] number (integer)
- "tier": one of "top", "next_best", or "skip", per the user's criteria above
- "reason": one sentence explaining the categorization (be specific — cite role fit, skills match, seniority, location, or deal-breakers)

Within each tier, order the elements from strongest to weakest match per the user's stated order of preference.

## Jobs
{jobs_text}"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    max_output_tokens = max(len(jobs) * 100 + 2000, 4096)

    with client.messages.stream(
        model=MODEL,
        max_tokens=max_output_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        response = stream.get_final_message()

    raw = next((b.text for b in response.content if b.type == "text"), "").strip()

    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        raw = raw.rsplit("```", 1)[0].strip()

    categorized = json.loads(raw)

    top, next_best = [], []
    for item in categorized:
        idx = int(item["index"])
        tier = item["tier"]
        reason = item["reason"]
        if idx >= len(jobs):
            continue
        job = jobs[idx]
        if tier == 'top':
            top.append(RankedJob(job=job, reason=reason, tier='top'))
        elif tier == 'next_best':
            next_best.append(RankedJob(job=job, reason=reason, tier='next_best'))

    logger.info(
        f"Ranked {len(jobs)} jobs: {len(top)} top, {len(next_best)} next best, "
        f"{len(jobs) - len(top) - len(next_best)} skipped"
    )
    return RankerResult(top=top, next_best=next_best)
