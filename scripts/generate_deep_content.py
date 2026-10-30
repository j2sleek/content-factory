#!/usr/bin/env python3
"""
Deep Content Generator using opencode
Creates highly engaging shorts and long-form content with research
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

class DeepContentGenerator:
    def __init__(self):
        self.sheet_id = os.environ.get('SHEET_ID')
        self.creds_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_path, scope)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(self.sheet_id)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    def get_deals(self):
        w = self.spreadsheet.worksheet('normalized_deals')
        recs = w.get_all_records()
        return [r for r in recs if r.get('Amount')]
    
    def scrape_article(self, url):
        try:
            r = self.session.get(url, timeout=30)
            soup = BeautifulSoup(r.content, 'html.parser')
            for tag in soup(['script','style','nav','footer','header','aside','iframe']):
                tag.decompose()
            art = soup.find('article') or soup.find('main') or soup.find('body')
            if art:
                text = art.get_text(strip=True, separator='\n')
                return '\n'.join([l.strip() for l in text.splitlines() if l.strip() and len(l.strip())>20][:60])
        except:
            pass
        return ""
    
    def create_deep_prompt(self, deal, article):
        name = deal.get('Startup Name') or deal.get('Title','').split()[0]
        amount = deal.get('Amount')
        currency = deal.get('Currency','USD')
        round_type = deal.get('Round','')
        countries = deal.get('Countries','')
        
        return f"""You are creating viral, engaging content about African startup funding for short-form video (TikTok, YouTube Shorts, Instagram Reels).

DEAL DATA:
- Startup: {name}
- Title: {deal.get('Title')}
- Amount Raised: {amount} {currency}
- Funding Round: {round_type}
- Location/Countries: {countries}
- Source URL: {deal.get('URL')}
- Source: {deal.get('Source')}

FULL ARTICLE CONTEXT:
{article}

YOUR TASK - Create highly engaging content:

## FOR SHORT-FORM (30-60 SECONDS, VERTICAL 9:16)

Create a script optimized for AI/human voiceover with:

1. **HOOK (0-5s)** - Strong hook that creates curiosity
   Example: "This African startup just raised $X million... here's why it matters"

2. **PROBLEM (5-12s)** - What problem does this solve in Africa?
   
3. **SOLUTION (12-20s)** - What does {name} do? Keep simple
   
4. **FUNDING NEWS (20-35s)** - The raise details, why investors are betting on them
   
5. **IMPACT & CTA (35-55s)** - Why this matters for Africa + "Follow for more African startup funding"

Requirements:
- Conversational, natural spoken English
- Use contractions (it's, they're)
- Write numbers for speech: "$2 million" not "$2M" where natural
- Short sentences (8-12 words max)
- Include natural pauses with punctuation
- Focus on IMPACT, not just the money
- Make it educational and inspiring

## OUTPUT FORMAT (JSON)
{{
  "deal_id": "{deal.get('ID')}",
  "startup_name": "{name}",
  "short_form": {{
    "hook": "...",
    "voiceover_script": "Full script with natural flow...",
    "caption": "Caption for post",
    "hashtags": ["#AfricanStartups", "#TechAfrica", "#{name.replace(' ','')}"],
    "visual_cues": [
      {{"time": "00:00", "action": "Show African map/highlight {countries}", "text": "HOOK TEXT"}},
      {{"time": "00:05", "action": "Show problem visualization", "text": ""}},
      {{"time": "00:12", "action": "Show {name} logo/product", "text": ""}},
      {{"time": "00:20", "action": "Show money/funding graphic", "text": ""}},
      {{"time": "00:35", "action": "Show impact/solution", "text": "CTA"}}
    ],
    "duration_seconds": 45,
    "on_screen_text": ["Hook text", "Key point", "CTA"]
  }},
  "weekly_roundup_entry": {{
    "headline": "One line summary for roundup",
    "summary": "2-3 sentences for roundup context",
    "why_it_matters": "Impact statement"
  }}
}}

Only use facts from the article. If information isn't available, say so briefly or skip. Make it compelling but accurate.
"""
    
    def generate_content(self):
        deals = self.get_deals()
        log_message(f"Generating content for {len(deals)} deals")
        
        # Ensure sheets exist
        try:
            self.spreadsheet.worksheet('shorts_scripts')
        except:
            w = self.spreadsheet.add_worksheet('shorts_scripts', 1000, 15)
            w.append_row(['Deal ID', 'Startup', 'Platform', 'Hook', 'Voiceover Script', 
                         'Caption', 'Hashtags', 'Visual Cues', 'On Screen Text', 
                         'Duration', 'Status', 'Generated At'])
        
        for deal in deals[:10]:
            name = deal.get('Startup Name') or 'Startup'
            article = self.scrape_article(deal.get('URL'))
            prompt = self.create_deep_prompt(deal, article)
            log_message(f"Prompt generated for {name} ({len(prompt)} chars)")
            # Save prompt for opencode to process
            with open(f'/tmp/prompt_{deal.get("ID")[:8]}.json', 'w') as f:
                json.dump({'deal': deal, 'prompt': prompt}, f)
        
        log_message("Prompts saved to /tmp/ for opencode processing")

def main():
    gen = DeepContentGenerator()
    gen.generate_content()

if __name__ == "__main__":
    main()
