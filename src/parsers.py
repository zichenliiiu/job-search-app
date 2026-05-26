# Pure parsing functions — no network I/O.
# Called by GmailFetcher after it retrieves raw email HTML from the Gmail API.
#
#   parse_linkedin_email(html)      → list[Job]  (called in GmailFetcher._fetch_linkedin_jobs)
#   parse_google_alert_email(html)  → list[Job]  (called in GmailFetcher._fetch_google_alert_jobs)
#                                      Handles both digest (multiple results) and as-it-happens
#                                      (single result per email) delivery formats.
#   extract_ats_description(soup)   → str        (called in GmailFetcher._fetch_description)
#   extract_company_from_url(url)   → str        (called inside parse_google_alert_email)
#   unwrap_google_redirect(url)     → str        (called inside parse_google_alert_email)

import json
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from src.job_class import Job

# Known ATS platforms that host jobs at jobs.<ats>.com/<company>/
_ATS_SUBDOMAINS = {
    'jobs.ashbyhq.com',
    'jobs.lever.co',
    'boards.greenhouse.io',
    'job-boards.greenhouse.io',
    'apply.workable.com',
    'jobs.jobvite.com',
}


def extract_company_from_url(url: str) -> str:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()

    # ATS-hosted: company slug is the first path segment
    if netloc in _ATS_SUBDOMAINS:
        parts = [p for p in parsed.path.split('/') if p]
        if parts:
            return parts[0].replace('-', ' ').title()

    # Use the label before the TLD so careers.datadoghq.com → datadoghq, not careers.
    host = re.sub(r'^www\.', '', netloc)
    parts = host.split('.')
    sld = parts[-2] if len(parts) >= 2 else parts[0]
    return sld.replace('-', ' ').title()


def unwrap_google_redirect(url: str) -> str:
    """Google Alert emails wrap outbound links in a google.com/url?q= redirect."""
    parsed = urlparse(url)
    if 'google.com' in parsed.netloc and parsed.path in ('/url', '/url/'):
        params = parse_qs(parsed.query)
        return params.get('q', params.get('url', [url]))[0]
    return url


def parse_linkedin_email(html: str) -> list[Job]:
    # NOTE: Only captures the 5-6 job preview in the alert email body, not the
    # full alert results. LinkedIn's Voyager search API is blocked as of 2025.
    soup = BeautifulSoup(html, 'lxml')
    jobs = []
    seen = set()

    for link in soup.find_all('a', href=re.compile(r'linkedin\.com.*?/jobs/view/')):
        url = link.get('href', '').strip()
        title = link.get_text(strip=True)
        if not url or not title or url in seen:
            continue
        seen.add(url)

        company, location = _linkedin_company_location(link)
        jobs.append(Job(title=title, company=company, location=location, url=url, source='linkedin'))

    return jobs


def _linkedin_company_location(link_tag) -> tuple[str, str]:
    # LinkedIn emails render company/location as "Company · Location" in a sibling element.
    # Walk up 3 ancestor levels to find it.
    company, location = '', ''
    node = link_tag.parent

    for _ in range(3):
        if node is None:
            break
        for sib in list(node.next_siblings)[:4]:
            text = sib.get_text(strip=True) if hasattr(sib, 'get_text') else str(sib).strip()
            if not text or text == link_tag.get_text(strip=True):
                continue
            if '·' in text:
                parts = [p.strip() for p in text.split('·', 1)]
                company, location = parts[0], parts[1]
            elif not company:
                company = text
            elif not location:
                location = text
            break
        if company:
            break
        node = node.parent

    return company, location


def _extract_google_snippet(link_tag, min_length: int = 30) -> str:
    """Find the closest substantial text block after a Google Alert result link.

    Walks up to 3 ancestor levels and checks following siblings at each level,
    returning the first text that is long enough to be a real snippet rather than
    a source/date line.  This handles both the digest (grouped list) and the
    as-it-happens (single-result table) email layouts.
    """
    node = link_tag.parent
    for _ in range(3):
        if node is None:
            break
        for sib in node.find_next_siblings():
            text = sib.get_text(strip=True) if hasattr(sib, 'get_text') else ''
            if len(text) >= min_length:
                return text[:300]
        node = node.parent
    return ''


def parse_google_alert_email(html: str) -> list[Job]:
    soup = BeautifulSoup(html, 'lxml')
    jobs = []
    seen = set()

    for link in soup.find_all('a', href=re.compile(r'https?://')):
        raw_url = link.get('href', '').strip()
        url = unwrap_google_redirect(raw_url)

        if not url or url in seen:
            continue
        if re.search(r'(google\.com|accounts\.google|support\.google|mailto:|googlealerts)', url, re.I):
            continue
        seen.add(url)

        title = link.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        jobs.append(Job(
            title=title,
            company=extract_company_from_url(url),
            location='',
            url=url,
            source='google_alerts',
            raw_snippet=_extract_google_snippet(link),
        ))

    return jobs


def extract_job_fields(soup: BeautifulSoup) -> dict:
    """Extract title, company, location, and description from an ATS page.

    Tries JSON-LD JobPosting schema first (Ashby, Lever, Greenhouse all emit it),
    then falls back to heuristics for each field individually.
    Returns a dict with keys: title, company, location, description.
    Any field that can't be detected is returned as an empty string.
    """
    result = {'title': '', 'company': '', 'location': '', 'description': ''}

    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
            if not (isinstance(data, dict) and data.get('@type') == 'JobPosting'):
                continue
            result['title'] = data.get('title') or data.get('name') or ''
            org = data.get('hiringOrganization') or {}
            result['company'] = org.get('name', '') if isinstance(org, dict) else ''
            loc = data.get('jobLocation') or {}
            if isinstance(loc, list):
                loc = loc[0] if loc else {}
            addr = loc.get('address') or {} if isinstance(loc, dict) else {}
            result['location'] = (
                addr.get('addressLocality') or
                addr.get('addressRegion') or
                data.get('workLocation') or ''
            ) if isinstance(addr, dict) else ''
            if 'description' in data:
                desc_soup = BeautifulSoup(data['description'], 'lxml')
                result['description'] = desc_soup.get_text(separator='\n', strip=True)
            return result
        except (json.JSONDecodeError, AttributeError):
            continue

    # JSON-LD not found — fall back to description-only extraction
    result['description'] = extract_ats_description(soup)
    return result


def extract_ats_description(soup: BeautifulSoup) -> str:
    # Many ATS platforms (Ashby, Lever, etc.) emit schema.org JobPosting JSON-LD
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
            if isinstance(data, dict) and data.get('@type') == 'JobPosting' and 'description' in data:
                desc_soup = BeautifulSoup(data['description'], 'lxml')
                return desc_soup.get_text(separator='\n', strip=True)
        except (json.JSONDecodeError, AttributeError):
            continue

    ats_selectors = [
        {'id': 'content'},                                               # Greenhouse
        {'class': re.compile(r'posting-description', re.I)},            # Lever
        {'data-automation-id': 'jobPostingDescription'},                 # Workday
        {'class': re.compile(r'job[-_]?description', re.I)},            # generic
        {'id': re.compile(r'job[-_]?description', re.I)},               # generic
        {'class': re.compile(r'job[-_]?details', re.I)},                # generic
    ]
    for selector in ats_selectors:
        section = soup.find(['div', 'section', 'article'], selector)
        if section:
            return section.get_text(separator='\n', strip=True)

    for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'noscript']):
        tag.decompose()
    body = soup.find('body') or soup
    return body.get_text(separator='\n', strip=True)[:5000]
