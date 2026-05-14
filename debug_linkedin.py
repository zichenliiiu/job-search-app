"""
Debug script: fetch a LinkedIn job description via the Voyager API.
Usage: python debug_linkedin.py <linkedin_job_url>
"""
import sys
import re
import os
import requests
from dotenv import load_dotenv

load_dotenv()
LI_AT = os.getenv('LINKEDIN_LI_AT')
JSESSIONID = os.getenv('LINKEDIN_JSESSIONID')

url = sys.argv[1] if len(sys.argv) > 1 else input("Paste a LinkedIn job URL: ").strip()

# Extract job ID from any LinkedIn job URL format
match = re.search(r'/jobs/view/(\d+)', url)
if not match:
    print("Could not extract job ID from URL")
    sys.exit(1)
job_id = match.group(1)
print(f"Job ID: {job_id}")

api_url = (
    f"https://www.linkedin.com/voyager/api/jobs/jobPostings/{job_id}"
    "?decorationId=com.linkedin.voyager.deco.jobs.web.shared.WebLightJobPosting-23"
)

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/vnd.linkedin.normalized+json+2.1',
    'x-li-lang': 'en_US',
    'x-restli-protocol-version': '2.0.0',
    'csrf-token': JSESSIONID,
}
cookies = {
    'li_at': LI_AT,
    'JSESSIONID': f'"{JSESSIONID}"',
}

print(f"Calling Voyager API...")
resp = requests.get(api_url, headers=headers, cookies=cookies, timeout=15)
print(f"Status: {resp.status_code}")

with open('data/debug_voyager.json', 'w') as f:
    f.write(resp.text)
print(f"Raw response saved to data/debug_voyager.json ({len(resp.text):,} chars)")

if resp.status_code == 200:
    data = resp.json()
    # Description lives at data.description.text
    desc = (data.get('data', {}) or data).get('description', {})
    text = desc.get('text', '') if isinstance(desc, dict) else ''
    if text:
        print(f"\nDescription ({len(text)} chars):\n{text[:500]}...")
    else:
        print("\nNo description found — check data/debug_voyager.json for the structure")
else:
    print(f"Error body: {resp.text[:500]}")
