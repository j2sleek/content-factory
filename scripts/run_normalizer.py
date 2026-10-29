#!/usr/bin/env python3
"""
GitHub Actions runner for normalizer
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.utils import extract_amount, extract_round, extract_countries, log_message

def main():
    run_id = str(uuid.uuid4())
    log_message(f"Starting normalization: {run_id}")
    
    # For GitHub Actions triggered flow, we might get items from payload
    # or pull from sheets - for now, this is a placeholder that can be triggered
    router_url = os.environ.get('APPS_SCRIPT_ROUTER_URL')
    if not router_url:
        log_message("APPS_SCRIPT_ROUTER_URL not set", "ERROR")
        sys.exit(1)
    
    # This would normally process items from the router payload
    payload = {
        "stage": "normalizer",
        "status": "completed",
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": 0,
        "items": [],
        "source": "github_actions_normalizer"
    }
    
    resp = requests.post(router_url, json=payload, timeout=60, headers={'Content-Type': 'application/json'})
    log_message(f"Router response: {resp.status_code}")
    print(resp.text)

if __name__ == "__main__":
    main()
