#!/usr/bin/env python3
"""
GitHub Actions runner for normalizer - Production Ready v2
Pulls items from Google Sheets, normalizes, enriches with article content scraping,
and prepares for AI enhancement with founder/research data
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.utils import extract_amount, extract_round, extract_countries, log_message, generate_id

class Normalizer:
    def __init__(self):
        self.sheet_id = os.environ.get('SHEET_ID')
        self.creds_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        self.router_url = os.environ.get('APPS_SCRIPT_ROUTER_URL')
        self.run_id = os.environ.get('RUN_ID') or str(uuid.uuid4())
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if not self.router_url:
            raise ValueError("APPS_SCRIPT_ROUTER_URL not set")
        
        if self.sheet_id and self.creds_path and os.path.exists(self.creds_path):
            self.setup_sheets()
        else:
            self.client = None
            self.spreadsheet = None
            log_message("Running without Google Sheets credentials - will only post to router", "WARNING")
    
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
                        'row_index': idx + 2
                    }
                    items.append(item)
            
            log_message(f"Found {len(items)} unprocessed items")
            return items
        except Exception as e:
            log_message(f"Error reading from sheets: {e}", "ERROR")
            return []
    
    def scrape_article_content(self, url):
        """Scrape full article content from the URL for better context"""
        if not url:
            return None
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove scripts, styles, ads
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            # Try to find article content
            article_selectors = [
                'article', '.post-content', '.entry-content', 
                '.article-content', '.content-body', 'main'
            ]
            
            content = ""
            for selector in article_selectors:
                elem = soup.select_one(selector)
                if elem:
                    content = elem.get_text(strip=True, separator=' ')
                    break
            
            if not content:
                content = soup.get_text(strip=True, separator=' ')
            
            # Clean up and limit
            content = re.sub(r'\s+', ' ', content)
            return content[:3000]  # Limit to 3000 chars
        except Exception as e:
            log_message(f"Failed to scrape article {url}: {e}", "WARNING")
            return None
    
    def is_funding_deal(self, title, content):
        """Check if this is actually a funding deal vs insights/metrics"""
        text = f"{title} {content or ''}".lower()
        
        # Funding indicators
        funding_words = ['raised', 'raises', 'funding', 'series', 'seed', 'investment', 
                        'capital', 'round', 'venture', 'financing']
        # Non-funding indicators (to filter out)
        exclude_words = ['insights', 'report', 'metrics', 'data shows', 'survey', 
                        'ranking', 'top', 'list of', 'analysis of']
        
        has_funding = any(word in text for word in funding_words)
        has_exclude = any(word in text for word in exclude_words)
        
        # If it has strong funding indicators and not just a report, it's likely a deal
        if has_funding and not (has_exclude and not any(w in text for w in ['raises', 'raised', 'secured'])):
            return True
        return has_funding
    
    def normalize_item(self, item):
        """Normalize and enrich a single item"""
        title = item.get('title', '')
        summary = item.get('summary', '')
        url = item.get('url', '')
        
        # Scrape full article content
        article_content = self.scrape_article_content(url)
        full_text = f"{title} {summary} {article_content or ''}"
        
        normalized = dict(item)
        
        # Check if it's actually a funding deal
        normalized['is_funding_deal'] = self.is_funding_deal(title, article_content)
        
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
        
        # Extract startup name
        if not normalized.get('startup_name') or normalized.get('startup_name') == 'normalized':
            # Try various patterns
            patterns = [
                r'^([A-Z][A-Za-z0-9\s&\.]{2,40}?)\s+(?:raises|secures|gets|closes|lands|attracts|banks)',
                r"([A-Z][A-Za-z0-9\s&\.]{2,40}?)['\u2019]s\s+",
                r'^([A-Z][A-Za-z0-9\s&\.]{2,40}?)\s+(?:Pre-Seed|Seed|Series)",
            ]
            for pattern in patterns:
                match = re.search(pattern, title)
                if match:
                    name = match.group(1).strip()
                    # Filter out common non-company words
                    if name.lower() not in ['nigeria', 'ghana', 'kenya', 'egypt', 'tanzania', 'africa']:
                        normalized['startup_name'] = name
                        break
            
            if not normalized.get('startup_name') or normalized.get('startup_name') == 'normalized':
                # Try to extract from "X's Y" pattern
                match = re.search(r'([A-Z][A-Za-z0-9\s&\.]{2,30}?)\s+(?:startup|platform|company)', title)
                if match:
                    normalized['startup_name'] = match.group(1).strip()
                else:
                    words = title.split()
                    # Take first capitalized word(s) that aren't location
                    candidates = []
                    for w in words[:4]:
                        if w[0].isupper() and w.lower() not in ['nigeria', 'ghana', 'kenya', 'egypt', 'tanzania', 'africa', 'the', 'how']:
                            candidates.append(w)
                    if candidates:
                        normalized['startup_name'] = ' '.join(candidates[:2])
        
        # Add enriched content for AI
        normalized['article_content'] = article_content[:1000] if article_content else summary
        normalized['full_context'] = full_text[:1500]
        
        normalized['status'] = 'normalized'
        normalized['normalized_at'] = datetime.now(timezone.utc).isoformat()
        normalized['run_id'] = self.run_id
        normalized['needs_enrichment'] = 'true'  # Flag for deeper AI research
        
        normalized.pop('row_index', None)
        
        return normalized
    
    def update_sheet_status(self, row_index):
        """Update status in raw_deals sheet"""
        if not self.spreadsheet or not row_index:
            return
        
        try:
            sheet = self.spreadsheet.worksheet('raw_deals')
            sheet.update_cell(row_index, 15, 'normalized')
        except Exception as e:
            log_message(f"Failed to update sheet: {e}", "WARNING")
    
    def run(self):
        """Main execution"""
        log_message(f"Normalizer starting - run_id: {self.run_id}")
        
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
                    # Only send actual funding deals to next stage
                    if normalized.get('is_funding_deal', True):
                        normalized_items.append(normalized)
                    else:
                        log_message(f"Skipping non-funding post: {normalized.get('title')[:50]}", "INFO")
                    if item.get('row_index') and self.spreadsheet:
                        self.update_sheet_status(item['row_index'])
                except Exception as e:
                    log_message(f"Error normalizing item {item.get('id')}: {e}", "ERROR")
                    continue
            
            log_message(f"Normalized {len(normalized_items)} funding deals")
            
            payload = {
                "stage": "normalizer",
                "status": "completed",
                "run_id": self.run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": len(normalized_items),
                "items": normalized_items,
                "source": "github_actions_normalizer"
            }
        
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
