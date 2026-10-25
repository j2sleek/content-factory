#!/usr/bin/env python3
"""
Google Cloud Function - Normalizer Stage
Enriches and normalizes deal data
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scrapers.utils import extract_amount, extract_round, extract_countries, log_message, generate_id

def normalize_handler(request):
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {'Access-Control-Allow-Origin': '*'}
    
    try:
        request_json = request.get_json(silent=True)
        run_id = request_json.get('run_id') if request_json else str(uuid.uuid4())
        
        log_message(f"Starting normalization: {run_id}")
        
        # Get items from request or fetch from sheets
        items = request_json.get('items', []) if request_json else []
        
        normalized_items = []
        for item in items:
            if item.get('status') != 'new':
                continue
            
            full_text = f"{item.get('title', '')} {item.get('summary', '')}"
            
            # Re-extract for accuracy
            amount_data = extract_amount(full_text)
            round_type = extract_round(full_text)
            countries = extract_countries(full_text)
            
            # Enhance item
            normalized = dict(item)
            if not normalized.get('amount') and amount_data.get('amount'):
                normalized['amount'] = amount_data['amount']
                normalized['currency'] = amount_data['currency']
                normalized['amount_usd'] = amount_data['amount_usd']
            if not normalized.get('round') and round_type:
                normalized['round'] = round_type
            if not normalized.get('countries') and countries:
                normalized['countries'] = ', '.join(countries)
            
            normalized['status'] = 'normalized'
            normalized['normalized_at'] = datetime.now(timezone.utc).isoformat()
            normalized_items.append(normalized)
        
        log_message(f"Normalized {len(normalized_items)} items")
        
        # Send to router
        router_url = os.environ.get('APPS_SCRIPT_ROUTER_URL')
        if not router_url:
            return (json.dumps({"error": "Router URL not configured"}), 500, headers)
        
        payload = {
            "stage": "normalizer",
            "status": "completed",
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(normalized_items),
            "items": normalized_items,
            "source": "gcf_normalizer"
        }
        
        import requests
        response = requests.post(router_url, json=payload, timeout=30, headers={'Content-Type': 'application/json'})
        
        return (json.dumps({
            "status": "success",
            "run_id": run_id,
            "normalized": len(normalized_items),
            "router_status": response.status_code
        }), 200, headers)
        
    except Exception as e:
        log_message(f"Error in normalizer: {str(e)}", "ERROR")
        return (json.dumps({"error": str(e)}), 500, headers)
