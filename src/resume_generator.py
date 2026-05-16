import html as html_lib
import json
import logging
from pathlib import Path

import anthropic

from config.config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-7"


def _load_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"File is empty: {path}")
    return text


def _call_claude(resume: str, job_description: str, prompt_instructions: str) -> dict:
    user_prompt = f"""\
## Candidate Resume
{resume}

## Job Description
{job_description}"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    with client.messages.stream(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[{
            "type": "text",
            "text": prompt_instructions,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        response = stream.get_final_message()

    raw = next((b.text for b in response.content if b.type == "text"), "").strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        raw = raw.rsplit("```", 1)[0].strip()

    return json.loads(raw)


def _build_html(data: dict) -> str:
    def esc(s):
        return html_lib.escape(str(s))

    header = data.get("header", {})
    header_html = (
        f'  <div class="header">\n'
        f'    <div class="header-name">{esc(header.get("name", ""))}</div>\n'
        f'    <div class="header-contact">{esc(header.get("contact", ""))}</div>\n'
        f'  </div>'
    )

    exp_blocks = []
    for exp in data.get("experiences", []):
        bullets_html = "\n".join(
            f"          <li>{esc(b)}</li>" for b in exp.get("bullets", [])
        )
        exp_blocks.append(
            f'      <div class="exp-block">\n'
            f'        <div class="exp-company">{esc(exp["company"])}</div>\n'
            f'        <div class="exp-role">{esc(exp["role"])}</div>\n'
            f'        <ul class="bullets">\n{bullets_html}\n        </ul>\n'
            f"      </div>"
        )

    edu = data.get("education", {})
    edu_lines_html = "\n".join(
        f'        <div class="edu-line">{esc(line)}</div>'
        for line in edu.get("lines", [])
    )
    edu_html = (
        f'      <div class="edu-block">\n'
        f'        <div class="edu-school">{esc(edu.get("school", ""))}</div>\n'
        f"{edu_lines_html}\n"
        f"      </div>"
    )

    experiences_html = "\n".join(exp_blocks)

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Resume</title>
  <style>
    @page {{
      size: letter;
      margin: 0.65in 0.75in;
    }}
    body {{
      font-family: Helvetica, Arial, sans-serif;
      font-size: 11pt;
      line-height: 1.4;
      color: #000;
      max-width: 750px;
      margin: 40px auto;
      padding: 0 20px;
    }}
    .section-title {{
      font-size: 1.05em;
      font-weight: bold;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1px solid #000;
      padding-bottom: 3px;
      margin-top: 22px;
      margin-bottom: 10px;
    }}
    .exp-block {{
      margin-bottom: 12px;
    }}
    .exp-company {{
      font-weight: bold;
    }}
    .exp-role {{
      font-style: italic;
      margin-bottom: 4px;
    }}
    .bullets {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}
    .bullets li {{
      padding-left: 1.2em;
      text-indent: -1.2em;
      margin-bottom: 3px;
    }}
    .bullets li::before {{
      content: "\\2013\\00A0";
    }}
    .edu-block {{
      margin-top: 6px;
    }}
    .edu-school {{
      font-weight: bold;
      margin-bottom: 2px;
    }}
    .edu-line {{
      margin-bottom: 2px;
    }}
    .header {{
      text-align: center;
      margin-bottom: 4px;
    }}
    .header-name {{
      font-size: 1.4em;
      font-weight: bold;
    }}
    .header-contact {{
      font-size: 0.95em;
      color: #333;
    }}
  </style>
</head>
<body>
{header_html}
  <div class="section-title">Professional Experience</div>
{experiences_html}
  <div class="section-title">Education</div>
{edu_html}
</body>
</html>"""


def generate_resume(job_description_path: str, output_path: str) -> str:
    """
    Generate a tailored resume as HTML.
    Returns the path of the written file.
    """
    resume = _load_text("config/resume.txt")
    job_description = _load_text(job_description_path)
    prompt_instructions = _load_text("config/resume_prompt.txt")

    logger.info("Calling Claude to tailor resume...")
    data = _call_claude(resume, job_description, prompt_instructions)

    html = _build_html(data)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html, encoding="utf-8")
    logger.info(f"Resume saved: {output_path}")

    return output_path
