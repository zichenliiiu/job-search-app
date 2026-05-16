#!/usr/bin/env python3
import argparse
import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from pathlib import Path

from src.resume_generator import generate_resume
from src.pdf_converter import convert_to_pdf


def main():
    parser = argparse.ArgumentParser(description="Generate a tailored resume HTML and PDF from a job description")
    parser.add_argument(
        "job_description",
        nargs="?",
        default="config/job_description.txt",
        help="Path to job description text file (default: config/job_description.txt)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Base output path without extension (default: output/resume_YYYYMMDD_HHMMSS)",
    )
    args = parser.parse_args()

    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"output/resume_{timestamp}"
    else:
        base = str(Path(args.output).with_suffix(""))

    try:
        html_path = generate_resume(args.job_description, f"{base}.html")
        print(f"HTML saved to: {html_path}")

        pdf_path = convert_to_pdf(html_path, f"{base}.pdf")
        print(f"PDF saved to:  {pdf_path}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
