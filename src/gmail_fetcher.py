import base64
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.config import GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, LINKEDIN_LI_AT, LINKEDIN_JSESSIONID

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
LINKEDIN_SENDER = 'jobalerts-noreply@linkedin.com'
GOOGLE_ALERTS_SENDER = 'googlealerts-noreply@google.com'


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str  # 'linkedin' or 'google_alerts'
    raw_snippet: str = ''
    description: str = ''
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    url_hash: str = field(init=False)

    def __post_init__(self):
        self.url_hash = hashlib.md5(self.url.encode()).hexdigest()


class GmailFetcher:
    def __init__(self):
        self.service = self._authenticate()
        self._last_fetched_ids: list[str] = []

    def _authenticate(self):
        creds = None
        if GMAIL_TOKEN_PATH and __import__('os').path.exists(GMAIL_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=8080)
            with open(GMAIL_TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    def fetch_all_jobs(self) -> list[Job]:
        linkedin_jobs, linkedin_ids = self._fetch_linkedin_jobs()
        google_jobs, google_ids = self._fetch_google_alert_jobs()

        self._last_fetched_ids = linkedin_ids + google_ids
        if self._last_fetched_ids:
            self._mark_as_read(self._last_fetched_ids)

        jobs = linkedin_jobs + google_jobs
        logger.info(f"Fetched {len(linkedin_jobs)} LinkedIn jobs, {len(google_jobs)} Google Alert jobs")
        return jobs

    def mark_last_batch_unread(self) -> None:
        if not self._last_fetched_ids:
            logger.info("No fetched emails to mark unread")
            return
        for i in range(0, len(self._last_fetched_ids), 1000):
            batch = self._last_fetched_ids[i:i + 1000]
            self.service.users().messages().batchModify(
                userId='me',
                body={'ids': batch, 'addLabelIds': ['UNREAD']},
            ).execute()
        logger.info(f"Marked {len(self._last_fetched_ids)} emails as unread")

    # --- Gmail helpers ---

    def _list_messages(self, query: str) -> list[dict]:
        result = self.service.users().messages().list(userId='me', q=query).execute()
        return result.get('messages', [])

    def _get_html_body(self, msg_id: str) -> Optional[str]:
        msg = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        return self._extract_html(msg.get('payload', {}))

    def _extract_html(self, payload: dict) -> Optional[str]:
        if payload.get('mimeType') == 'text/html':
            data = payload.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        for part in payload.get('parts', []):
            html = self._extract_html(part)
            if html:
                return html
        return None

    def _mark_as_read(self, msg_ids: list[str]) -> None:
        # batchModify accepts up to 1000 IDs at a time
        for i in range(0, len(msg_ids), 1000):
            batch = msg_ids[i:i + 1000]
            self.service.users().messages().batchModify(
                userId='me',
                body={'ids': batch, 'removeLabelIds': ['UNREAD']},
            ).execute()
        logger.info(f"Marked {len(msg_ids)} emails as read")

    # --- LinkedIn ---

    def _fetch_linkedin_jobs(self) -> tuple[list[Job], list[str]]:
        messages = self._list_messages(f'from:{LINKEDIN_SENDER} is:unread')
        jobs, msg_ids = [], []
        for msg in messages:
            html = self._get_html_body(msg['id'])
            if html:
                jobs.extend(self._parse_linkedin_email(html))
                msg_ids.append(msg['id'])
        return jobs, msg_ids

    def _parse_linkedin_email(self, html: str) -> list[Job]:
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

            company, location = self._linkedin_company_location(link)
            jobs.append(Job(title=title, company=company, location=location, url=url, source='linkedin'))

        return jobs

    def _linkedin_company_location(self, link_tag) -> tuple[str, str]:
        """
        LinkedIn emails typically render company and location as either:
          - "Company · Location" text in an adjacent sibling element, or
          - Separate sibling elements after the job title link.
        Walk up 3 ancestor levels looking for that text.
        """
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

    # --- Google Alerts ---

    def _fetch_google_alert_jobs(self) -> tuple[list[Job], list[str]]:
        messages = self._list_messages(f'from:{GOOGLE_ALERTS_SENDER} is:unread')
        jobs, msg_ids = [], []
        for msg in messages:
            html = self._get_html_body(msg['id'])
            if html:
                jobs.extend(self._parse_google_alert_email(html))
                msg_ids.append(msg['id'])
        return jobs, msg_ids

    def _parse_google_alert_email(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, 'lxml')
        jobs = []
        seen = set()

        # Alert name is usually in an <h2> or a prominent header cell
        alert_name = ''
        for tag in soup.find_all(['h2', 'h3']):
            text = tag.get_text(strip=True)
            if text:
                alert_name = text
                break

        # Each result is an <a> linking out via Google's redirect
        for link in soup.find_all('a', href=re.compile(r'https?://')):
            raw_url = link.get('href', '').strip()
            url = self._unwrap_google_redirect(raw_url)

            # Skip Google-internal and utility links
            if not url or url in seen:
                continue
            if re.search(r'(google\.com|accounts\.google|support\.google|mailto:)', url):
                continue
            seen.add(url)

            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            # Grab snippet from the next sibling block
            snippet = ''
            parent = link.parent
            if parent:
                sib = parent.find_next_sibling()
                if sib:
                    snippet = sib.get_text(strip=True)[:300]

            jobs.append(Job(
                title=title,
                company=alert_name,
                location='',
                url=url,
                source='google_alerts',
                raw_snippet=snippet,
            ))

        return jobs

    # --- Job description fetching ---

    _SCRAPE_HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/',
    }

    def enrich_with_descriptions(self, jobs: list[Job], delay: float = 1.5) -> None:
        """Fetch and attach job descriptions in-place. delay=seconds between requests."""
        session = requests.Session()
        session.headers.update(self._SCRAPE_HEADERS)

        for i, job in enumerate(jobs):
            if i > 0:
                time.sleep(delay)
            job.description = self._fetch_description(session, job.url)
            logger.info(f"[{i + 1}/{len(jobs)}] {job.title}: {len(job.description)} chars")

    def _fetch_description(self, session: requests.Session, url: str) -> str:
        try:
            if 'linkedin.com' in url:
                return self._fetch_linkedin_description_voyager(url)
            resp = session.get(url, timeout=15, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            return self._extract_ats_description(soup)
        except Exception as e:
            logger.warning(f"Could not fetch description for {url}: {e}")
            return ''

    @staticmethod
    def _fetch_linkedin_description_voyager(url: str) -> str:
        match = re.search(r'/jobs/view/(\d+)', url)
        if not match:
            return ''
        job_id = match.group(1)

        api_url = (
            f"https://www.linkedin.com/voyager/api/jobs/jobPostings/{job_id}"
            "?decorationId=com.linkedin.voyager.deco.jobs.web.shared.WebLightJobPosting-23"
        )
        resp = requests.get(
            api_url,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/vnd.linkedin.normalized+json+2.1',
                'x-li-lang': 'en_US',
                'x-restli-protocol-version': '2.0.0',
                'csrf-token': LINKEDIN_JSESSIONID,
            },
            cookies={
                'li_at': LINKEDIN_LI_AT,
                'JSESSIONID': f'"{LINKEDIN_JSESSIONID}"',
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        desc = (data.get('data') or data).get('description', {})
        return desc.get('text', '') if isinstance(desc, dict) else ''

    @staticmethod
    def _extract_ats_description(soup: BeautifulSoup) -> str:
        # Many ATS platforms (Ashby, Lever, etc.) emit schema.org JobPosting JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                if isinstance(data, dict) and data.get('@type') == 'JobPosting' and 'description' in data:
                    desc_soup = BeautifulSoup(data['description'], 'lxml')
                    return desc_soup.get_text(separator='\n', strip=True)
            except (json.JSONDecodeError, AttributeError):
                continue

        # Try known ATS containers before falling back to full body
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

        # Full-body fallback: strip boilerplate tags then grab text
        for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'noscript']):
            tag.decompose()
        body = soup.find('body') or soup
        return body.get_text(separator='\n', strip=True)[:5000]

    @staticmethod
    def _unwrap_google_redirect(url: str) -> str:
        """Google Alert emails wrap outbound links in a google.com/url?q= redirect."""
        parsed = urlparse(url)
        if 'google.com' in parsed.netloc and parsed.path in ('/url', '/url/'):
            params = parse_qs(parsed.query)
            return params.get('q', params.get('url', [url]))[0]
        return url
