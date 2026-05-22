# Gmail API client and job description scraper.
# Entry point: GmailFetcher — instantiate once per run, then call:
#
#   fetch_all_jobs()  reads unread LinkedIn + Google Alert emails → list[Job]
#   enrich(jobs)      fetches descriptions and resolves LinkedIn URLs to ATS URLs in-place
#   mark_last_batch_unread()  rolls back read-marks (useful during testing)
#
# Parsing email HTML is delegated to src/parsers.py.
# The Job dataclass is defined in src/job_class.py.

import base64
import hashlib
import logging
import re
import time
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.config import GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, LINKEDIN_LI_AT, LINKEDIN_JSESSIONID
from src.job_class import Job
from src.parsers import extract_ats_description, parse_google_alert_email, parse_linkedin_email

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
LINKEDIN_SENDER = 'jobalerts-noreply@linkedin.com'
GOOGLE_ALERTS_SENDER = 'googlealerts-noreply@google.com'

# strips "source = linkedin"
def _strip_source_param(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop('source', None)
    return urlunparse(parsed._replace(query=urlencode({k: v[0] for k, v in params.items()})))


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
                jobs.extend(parse_linkedin_email(html))
                msg_ids.append(msg['id']) # each email has a msg_id
        return jobs, msg_ids

    # --- Google Alerts ---

    def _fetch_google_alert_jobs(self) -> tuple[list[Job], list[str]]:
        messages = self._list_messages(f'from:{GOOGLE_ALERTS_SENDER} is:unread')
        jobs, msg_ids = [], []
        for msg in messages:
            html = self._get_html_body(msg['id'])
            if html:
                jobs.extend(parse_google_alert_email(html))
                msg_ids.append(msg['id'])
        return jobs, msg_ids

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

    def enrich(self, jobs: list[Job], delay: float = 1.5) -> None:
        session = requests.Session()
        session.headers.update(self._SCRAPE_HEADERS)

        for i, job in enumerate(jobs):
            if i > 0:
                time.sleep(delay)
            if job.source == 'linkedin':
                match = re.search(r'/jobs/view/(\d+)', job.url)
                if match:
                    data = self._fetch_linkedin_voyager_data(match.group(1))
                    job.description = self._parse_linkedin_description(data)
                    ats_url = self._parse_linkedin_ats_url(data)
                    if ats_url:
                        job.url = ats_url
                        job.url_hash = hashlib.md5(ats_url.encode()).hexdigest()
            else:
                job.description = self._fetch_ats_description(session, job.url)
            logger.info(f"[{i + 1}/{len(jobs)}] {job.title}: {len(job.description)} chars")

    def _fetch_ats_description(self, session: requests.Session, url: str) -> str:
        try:
            resp = session.get(url, timeout=15, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            return extract_ats_description(soup)
        except Exception as e:
            logger.warning(f"Could not fetch description for {url}: {e}")
            return ''

    @staticmethod
    def _fetch_linkedin_voyager_data(job_id: str) -> dict:
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
        return resp.json()

    @staticmethod
    def _parse_linkedin_description(data: dict) -> str:
        job_data = data.get('data') or data
        desc = job_data.get('description', {})
        return desc.get('text', '') if isinstance(desc, dict) else ''

    @staticmethod
    def _parse_linkedin_ats_url(data: dict) -> Optional[str]:
        job_data = data.get('data') or data
        apply_method = job_data.get('applyMethod', {})
        if apply_method.get('$type') == 'com.linkedin.voyager.jobs.OffsiteApply':
            url = apply_method.get('companyApplyUrl', '')
            if url:
                return _strip_source_param(url)
        return None
