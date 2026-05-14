"""
Debug script: test the LinkedIn Voyager job search API.
Calls the search endpoint with params extracted from a LinkedIn alert email URL,
and saves the raw response so we can inspect the structure.
Usage: python debug_linkedin_search.py <"see all jobs" URL from a LinkedIn alert email>
"""
import sys
import json
import os
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()
LI_AT = os.getenv('LINKEDIN_LI_AT')
JSESSIONID = os.getenv('LINKEDIN_JSESSIONID')

url = sys.argv[1] if len(sys.argv) > 1 else input('Paste a LinkedIn alert "See all jobs" URL: ').strip()

qs = parse_qs(urlparse(url).query)
geo_id     = qs.get('geoId', [''])[0]
company_ids = qs.get('f_C', [])
f_tpr      = qs.get('f_TPR', [''])[0]

print(f"geo_id:      {geo_id}")
print(f"company_ids: {company_ids}")
print(f"f_tpr:       {f_tpr}")

# Convert f_TPR (e.g. "a1747000000-") to seconds-since range for Voyager
import re, time
tpr_match = re.match(r'a(\d+)-?', f_tpr)
if tpr_match:
    posted_after_ts = int(tpr_match.group(1))
    seconds_since = max(int(time.time()) - posted_after_ts, 3600)
    time_filter = f'r{seconds_since}'
else:
    time_filter = 'r604800'  # fallback: last 7 days
print(f"time_filter: {time_filter}")

company_list = ','.join(company_ids)
query = (
    f'(origin:JOB_ALERT_EMAIL,'
    f'selectedFilters:(company:List({company_list}),'
    f'timePostedRange:List({time_filter})),'
    f'spellCorrectionEnabled:true)'
)
location = f'(geoId:{geo_id})' if geo_id else '(geoId:92000000)'

api_url = 'https://www.linkedin.com/voyager/api/jobs/search'
params = {
    'decorationId': 'com.linkedin.voyager.deco.jobs.web.shared.WebLightJobPosting-23',
    'q': 'jobSearch',
    'query': query,
    'locationUnion': location,
    'count': 25,
    'start': 0,
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/vnd.linkedin.normalized+json+2.1',
    'x-li-lang': 'en_US',
    'x-restli-protocol-version': '2.0.0',
    'csrf-token': JSESSIONID,
}
cookies = {
    'li_at': LI_AT,
    'JSESSIONID': f'"{JSESSIONID}"',
}

print(f"\nCalling Voyager search API...")
resp = requests.get(api_url, params=params, headers=headers, cookies=cookies, timeout=15)
print(f"Status: {resp.status_code}")

with open('data/debug_search.json', 'w') as f:
    f.write(resp.text)
print(f"Raw response saved to data/debug_search.json ({len(resp.text):,} chars)")

if resp.status_code == 200:
    data = resp.json()

    # Inspect top-level keys
    print(f"\nTop-level keys: {list(data.keys())}")

    # Paging info
    paging = data.get('data', {}).get('paging') or data.get('paging', {})
    print(f"Paging: {paging}")

    # Count elements
    elements = data.get('data', {}).get('elements', []) or data.get('elements', [])
    included = data.get('included', [])
    print(f"data.elements count: {len(elements)}")
    print(f"included count:      {len(included)}")

    # Show types in included
    types = {}
    for item in included:
        t = item.get('$type', 'unknown')
        types[t] = types.get(t, 0) + 1
    print(f"included $types: {types}")

    # Preview first job-like item
    for item in included:
        if 'JobPosting' in item.get('$type', '') or 'title' in item:
            print(f"\nFirst job-like item keys: {list(item.keys())}")
            print(f"  title:    {item.get('title')}")
            print(f"  entityUrn: {item.get('entityUrn')}")
            break
else:
    print(f"Error: {resp.text[:500]}")
