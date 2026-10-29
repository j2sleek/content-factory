#!/usr/bin/env python3
"""
GitHub Actions runner for scraper
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.rss_scraper import RSScraper
from scrapers.html_scraper import HTMLScraper
from scrapers.utils import log_message

def main():
    run_id = str(uuid.uuid4())
    log_message(f"Starting scrape run: {run_id}")
    
    rss_scraper = RSScraper()
    rss_deals = rss_scraper.scrape_all()
    
    html_scraper = HTMLScraper()
    html_deals = html_scraper.scrape_all()
    
    all_deals = rss_deals + html_deals
    
    # Deduplicate
    seen = set()
    unique = []
    for d in all_deals:
        if d['id'] not in seen:
            seen.add(d['id'])
            unique.append(d)
    
    log_message(f"Scraped {len(unique)} unique deals")
    
    router_url = os.environ.get('APPS_SCRIPT_ROUTER_URL')
    if not router_url:
        log_message("APPS_SCRIPT_ROUTER_URL not set", "ERROR")
        sys.exit(1)
    
    payload = {
        "stage": "scraper",
        "status": "completed",
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(unique),
        "items": unique,
        "source": "github_actions_scraper"
    }
    
    resp = requests.post(router_url, json=payload, timeout=60, headers={'Content-Type': 'application/json'})
    log_message(f"Router response: {resp.status_code}")
    print(resp.text)

if __name__ == "__main__":
    main()
