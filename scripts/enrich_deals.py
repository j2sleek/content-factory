#!/usr/bin/env python3
"""
Deep Research Enrichment using opencode
Scrapes article content, researches founders, products, valuation, use of funds
"""
import json
import os
import sys
from datetime import datetime, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.utils import log_message

class DealEnricher:
    def __init__(self):
        self.sheet_id = os.environ.get('SHEET_ID')
        self.creds_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.setup_sheets()
    
    def setup_sheets(self):
        scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_path, scope)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(self.sheet_id)
    
    def get_deals_to_enrich(self):
        try:
            sheet = self.spreadsheet.worksheet('normalized_deals')
            records = sheet.get_all_records()
            deals = []
            for idx, r in enumerate(records):
                if r.get('Amount') and r.get('Status'):
                    deals.append({**r, '_row': idx + 2})
            return deals
        except Exception as e:
            log_message(f"Error: {e}", "ERROR")
            return []
    
    def scrape_full_article(self, url):
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                tag.decompose()
            article = soup.find('article') or soup.find(class_=lambda x: x and 'content' in str(x).lower())
            if article:
                text = article.get_text(strip=True, separator='\n')
            else:
                text = soup.get_text(strip=True, separator='\n')
            return '\n'.join([l.strip() for l in text.splitlines() if l.strip()][:80])
        except Exception as e:
            return None
    
    def generate_enrichment_prompt(self, deal, article_text):
        return f"""Research and extract detailed information about this African startup funding deal for content creation.

DEAL INFO:
- Title: {deal.get('Title')}
- Startup: {deal.get('Startup Name')}
- Amount: {deal.get('Amount')} {deal.get('Currency')}
- Round: {deal.get('Round')}
- Countries: {deal.get('Countries')}
- Source: {deal.get('Source')}
- URL: {deal.get('URL')}

ARTICLE CONTENT:
{article_text[:2000] if article_text else deal.get('Summary', '')}

TASK:
Extract and research the following:
1. STARTUP OVERVIEW - What does this company do? Core product/service?
2. FOUNDERS - Who founded it? Background if mentioned
3. PROBLEM SOLVED - What problem are they addressing in Africa?
4. MARKET - Target market and opportunity
5. USE OF FUNDS - How will they use the investment?
6. GROWTH PLANS - Expansion plans mentioned?
7. COMPETITORS/CONTEXT - Market position
8. IMPACT - How does this help African ecosystem?
9. KEY QUOTE - Any notable quote from founder/investor
10. STORY ANGLE - Best angle for engaging short-form content

Provide detailed, factual information. Only use what's in article or can be reasonably inferred. Mark unknowns as "Not specified".

Format as JSON with these keys: overview, founders, problem, market, use_of_funds, growth_plans, competitors, impact, key_quote, story_angle, hooks
"""

def main():
    enricher = DealEnricher()
    deals = enricher.get_deals_to_enrich()
    log_message(f"Found {len(deals)} deals to enrich")
    
    for deal in deals[:5]:  # Start with top 5
        log_message(f"Enriching: {deal.get('Startup Name')} - {deal.get('Title')[:60]}")
        article = enricher.scrape_full_article(deal.get('URL'))
        prompt = enricher.generate_enrichment_prompt(deal, article)
        print("\n" + "="*60)
        print(prompt[:500] + "...")
        print("="*60 + "\n")

if __name__ == "__main__":
    main()
