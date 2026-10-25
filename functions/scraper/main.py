#!/usr/bin/env python3
"""
Google Cloud Function - Scraper Stage
Triggered by Cloud Scheduler via HTTP
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scrapers.rss_scraper import RSScraper
from scrapers.html_scraper import HTMLScraper
from scrapers.utils import log_message

def scrape_handler(request):
    """
    HTTP Cloud Function to scrape African startup funding news
    """
    # Set CORS headers for preflight requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*'
    }
    
    try:
        run_id = str(uuid.uuid4())
        log_message(f"Starting scrape run: {run_id}")
        
        # Scrape RSS feeds
        rss_scraper = RSScraper()
        rss_deals = rss_scraper.scrape_all()
        
        # Scrape HTML sources as fallback
        html_scraper = HTMLScraper()
        html_deals = html_scraper.scrape_all()
        
        all_deals = rss_deals + html_deals
        
        # Deduplicate by ID
        seen_ids = set()
        unique_deals = []
        for deal in all_deals:
            if deal['id'] not in seen_ids:
                seen_ids.add(deal['id'])
                unique_deals.append(deal)
        
        log_message(f"Scraped {len(unique_deals)} unique deals")
        
        # Send to Apps Script router
        router_url = os.environ.get('APPS_SCRIPT_ROUTER_URL')
        if not router_url:
            log_message("APPS_SCRIPT_ROUTER_URL not set", "ERROR")
            return (json.dumps({"error": "Router URL not configured"}), 500, headers)
        
        payload = {
            "stage": "scraper",
            "status": "completed",
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(unique_deals),
            "items": unique_deals,
            "source": "gcf_scraper"
        }
        
        import requests
        response = requests.post(
            router_url,
            json=payload,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        log_message(f"Router response: {response.status_code}")
        
        return (json.dumps({
            "status": "success",
            "run_id": run_id,
            "deals_scraped": len(unique_deals),
            "router_status": response.status_code
        }), 200, headers)
        
    except Exception as e:
        log_message(f"Error in scraper: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return (json.dumps({"error": str(e)}), 500, headers)
