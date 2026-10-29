#!/usr/bin/env python3
"""
GitHub Actions runner for normalizer - Production Ready
Pulls items from Google Sheets or processes webhook payload, normalizes and enriches data
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.utils import extract_amount, extract_round, extract_countries, log_message, generate_id

class Normalizer:
    def __init__(self):
        self.sheet_id = os.environ.get('SHEET_ID')
        self.creds_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        self.router_url = os.environ.get('APPS_SCRIPT_ROUTER_URL')
        self.run_id = os.environ.get('RUN_ID') or str(uuid.uuid4())
        
        if not self.router_url:
            raise ValueError("APPS_SCRIPT_ROUTER_URL not set")
        
        if self.sheet_id and self.creds_path:
            self.setup_sheets()
        else:
            self.client = None
            self.spreadsheet = None
    
    def setup_sheets(self):
        """Setup Google Sheets connection"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_path, scope)
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.sheet_id)
            log_message("Connected to Google Sheets")
        except Exception as e:
            log_message(f"Failed to connect to sheets: {e}", "ERROR")
            self.client = None
            self.spreadsheet = None
    
    def get_unprocessed_items(self):
        """Get unprocessed items from raw_deals sheet"""
        if not self.spreadsheet:
            return []
        
        try:
            sheet = self.spreadsheet.worksheet('raw_deals')
            records = sheet.get_all_records()
            items = []
            
            for idx, record in enumerate(records):
                status = record.get('Status', '').lower()
                if status in ['new', '']:
                    item = {
                        'id': record.get('ID'),
                        'source': record.get('Source'),
                        'title': record.get('Title'),
                        'url': record.get('URL'),
                        'summary': record.get('Summary'),
                        'published_at': record.get('Published At'),
                        'scraped_at': record.get('Scraped At'),
                        'amount': record.get('Amount'),
                        'currency': record.get('Currency'),
                        'amount_usd': record.get('Amount USD'),
                        'round': record.get('Round'),
                        'countries': record.get('Countries'),
                        'sector': record.get('Sector'),
                        'investors': record.get('Investors'),
                        'row_index': idx + 2  # 1-based + header
                    }
                    items.append(item)
            
            log_message(f"Found {len(items)} unprocessed items")
            return items
        except Exception as e:
            log_message(f"Error reading from sheets: {e}", "ERROR")
            return []
    
    def normalize_item(self, item):
        """Normalize and enrich a single item"""
        title = item.get('title', '')
        summary = item.get('summary', '')
        full_text = f"{title} {summary}"
        
        normalized = dict(item)
        
        # Extract/enhance amount
        if not normalized.get('amount') or normalized.get('amount') == '':
            amount_data = extract_amount(full_text)
            if amount_data.get('amount'):
                normalized['amount'] = amount_data['amount']
                normalized['currency'] = amount_data['currency']
                normalized['amount_usd'] = amount_data['amount_usd']
                normalized['amount_raw'] = amount_data.get('raw_match')
        
        # Extract/enhance round
        if not normalized.get('round') or normalized.get('round') == '':
            round_type = extract_round(full_text)
            if round_type:
                normalized['round'] = round_type
        
        # Extract/enhance countries
        if not normalized.get('countries') or normalized.get('countries') == '':
            countries = extract_countries(full_text)
            if countries:
                normalized['countries'] = ', '.join(countries)
        
        # Extract startup name from title (basic heuristic)
        if not normalized.get('startup_name'):
            # Try to extract company name patterns
            import re
            # Look for patterns like "Startup X raises", "X raises", etc.
            match = re.search(r'^([A-Z][A-Za-z0-9\s&]+?)\s+(?:raises|secures|gets|closes)', title)
            if match:
                normalized['startup_name'] = match.group(1).strip()
            else:
                # Fallback: first few words if capitalized
                words = title.split()
                if len(words) >= 2 and words[0][0].isupper():
                    normalized['startup_name'] = ' '.join(words[:2])
        
        normalized['status'] = 'normalized'
        normalized['normalized_at'] = datetime.now(timezone.utc).isoformat()
        normalized['run_id'] = self.run_id
        
        # Clean up
        normalized.pop('row_index', None)
        
        return normalized
    
    def update_sheet_status(self, row_index):
        """Update status in raw_deals sheet"""
        if not self.spreadsheet or not row_index:
            return
        
        try:
            sheet = self.spreadsheet.worksheet('raw_deals')
            # Status is column 15 (O)
            sheet.update_cell(row_index, 15, 'normalized')
        except Exception as e:
            log_message(f"Failed to update sheet: {e}", "WARNING")
    
    def run(self):
        """Main execution"""
        log_message(f"Normalizer starting - run_id: {self.run_id}")
        
        # Get items to process
        items = self.get_unprocessed_items()
        
        if not items:
            log_message("No items to normalize")
            payload = {
                "stage": "normalizer",
                "status": "completed",
                "run_id": self.run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": 0,
                "items": [],
                "source": "github_actions_normalizer"
            }
        else:
            normalized_items = []
            for item in items:
                try:
                    normalized = self.normalize_item(item)
                    normalized_items.append(normalized)
                    if item.get('row_index'):
                        self.update_sheet_status(item['row_index'])
                except Exception as e:
                    log_message(f"Error normalizing item {item.get('id')}: {e}", "ERROR")
                    continue
            
            log_message(f"Normalized {len(normalized_items)} items")
            
            payload = {
                "stage": "normalizer",
                "status": "completed",
                "run_id": self.run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": len(normalized_items),
                "items": normalized_items,
                "source": "github_actions_normalizer"
            }
        
        # Send to router
        try:
            resp = requests.post(
                self.router_url, 
                json=payload, 
                timeout=60, 
                headers={'Content-Type': 'application/json'}
            )
            log_message(f"Router response: {resp.status_code}")
            print(resp.text)
        except Exception as e:
            log_message(f"Failed to send to router: {e}", "ERROR")
            sys.exit(1)

def main():
    normalizer = Normalizer()
    normalizer.run()

if __name__ == "__main__":
    main()
