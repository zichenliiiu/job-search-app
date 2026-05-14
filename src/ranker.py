import json
import logging
from dataclasses import dataclass
from pathlib import Path

import anthropic

from config.config import ANTHROPIC_API_KEY
from src.gmail_fetcher import Job

logger = logging.getLogger(__name__)

TOP_THRESHOLD = 75
NEXT_BEST_FLOOR = 40
DEFAULT_DESC_CAP = 1500
TOKEN_BUDGET = 190_000
MODEL = "claude-opus-4-7"


@dataclass
class RankedJob:
    job: Job
    score: int
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

    system_prompt = f"""You are evaluating job postings for a candidate. Score each job 0-100 based on how well it matches their resume and what they are looking for.

## What the candidate is looking for
{criteria}

## Candidate's resume
{resume}"""

    user_prompt = f"""Evaluate the {len(jobs)} job postings below. Return ONLY a JSON array — no prose, no markdown fences.

Each element must have:
- "index": the job's [N] number (integer)
- "score": integer 0-100
- "reason": one sentence explaining the score (be specific — cite role fit, skills match, seniority, location, or deal-breakers)

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

    scores = json.loads(raw)

    top, next_best = [], []
    for item in scores:
        idx = int(item["index"])
        score = int(item["score"])
        reason = item["reason"]
        if idx >= len(jobs):
            continue
        job = jobs[idx]
        if score >= TOP_THRESHOLD:
            top.append(RankedJob(job=job, score=score, reason=reason, tier='top'))
        elif score >= NEXT_BEST_FLOOR:
            next_best.append(RankedJob(job=job, score=score, reason=reason, tier='next_best'))

    top.sort(key=lambda x: x.score, reverse=True)
    next_best.sort(key=lambda x: x.score, reverse=True)

    logger.info(
        f"Ranked {len(jobs)} jobs: {len(top)} top, {len(next_best)} next best, "
        f"{len(jobs) - len(top) - len(next_best)} dropped (score < {NEXT_BEST_FLOOR})"
    )
    return RankerResult(top=top, next_best=next_best)
