import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

FONT_SIZES = [10.5, 10.0, 9.5, 9.0]


def _set_font_size(html: str, font_size: float) -> str:
    # The HTML template has exactly one `font-size: Xpt` (on body).
    # All other sizes are relative (em), so this swap is safe.
    return re.sub(r"font-size: [\d.]+pt", f"font-size: {font_size}pt", html)


def _page_count(html: str) -> int:
    from weasyprint import HTML
    return len(HTML(string=html).render().pages)


def convert_to_pdf(html_path: str, pdf_path: str) -> str:
    """
    Convert an HTML resume to a one-page PDF.
    Scales font size down if content overflows one page.
    Returns the path of the written PDF.
    """
    html = Path(html_path).read_text(encoding="utf-8")

    chosen_html = None
    for font_size in FONT_SIZES:
        candidate = _set_font_size(html, font_size)
        pages = _page_count(candidate)
        if pages == 1:
            chosen_html = candidate
            logger.info(f"Fits on 1 page at {font_size}pt")
            break
        logger.info(f"Overflows at {font_size}pt ({pages} pages); trying smaller...")

    if chosen_html is None:
        logger.warning(f"Still overflows at {FONT_SIZES[-1]}pt; using minimum font size")
        chosen_html = _set_font_size(html, FONT_SIZES[-1])

    from weasyprint import HTML
    Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)
    HTML(string=chosen_html).write_pdf(pdf_path)
    logger.info(f"PDF saved: {pdf_path}")
    return pdf_path
