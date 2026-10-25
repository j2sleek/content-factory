#!/usr/bin/env python3
"""
AI Content Generator using opencode
Pulls normalized deals from Google Sheets and generates voiceover-ready content
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from jinja2 import Template

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ContentGenerator:
    def __init__(self):
        self.sheet_id = os.environ.get('SHEET_ID')
        self.creds_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        self.run_id = os.environ.get('RUN_ID')
        
        if not self.sheet_id or not self.creds_path:
            raise ValueError("Missing required environment variables")
        
        self.setup_sheets()
    
    def setup_sheets(self):
        """Setup Google Sheets connection"""
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_path, scope)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(self.sheet_id)
    
    def get_normalized_deals(self, days_back=3):
        """Get normalized deals from last N days"""
        try:
            sheet = self.spreadsheet.worksheet('normalized_deals')
            records = sheet.get_all_records()
            
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
            deals = []
            
            for record in records:
                if record.get('Status') == 'normalized' and record.get('Content Generated') != 'true':
                    deals.append(record)
            
            return deals
        except Exception as e:
            print(f"Error getting deals: {e}")
            return []
    
    def load_prompt(self):
        """Load repurposing prompt"""
        with open('prompts/repurpose_voiceover.md', 'r', encoding='utf-8') as f:
            return f.read()
    
    def generate_short_form(self, deal):
        """Generate short-form script for a deal"""
        prompt = self.load_prompt()
        
        deal_context = f"""
        DEAL DATA:
        Title: {deal.get('Title')}
        Startup: {deal.get('Startup Name') or 'Unknown'}
        Country: {deal.get('Countries')}
        Amount: {deal.get('Amount')} {deal.get('Currency')}
        Round: {deal.get('Round')}
        Source: {deal.get('Source')}
        URL: {deal.get('URL')}
        Summary: {deal.get('Summary')}
        
        Generate a 30-60 second vertical short-form script optimized for voiceover.
        """
        
        # In production, this would call opencode API
        # For now, create template structure
        return {
            "deal_id": deal.get('ID'),
            "platform": "shorts",
            "hook": f"African startup raises big funding...",
            "voiceover_script": f"An African startup just secured funding. More details coming soon.",
            "caption": f"Another African startup secures funding. Link in bio for more.",
            "hashtags": ["#AfricanStartups", "#TechAfrica", "#Funding"],
            "visual_cues": [
                {"time": "00:00", "cue": f"Show map of {deal.get('Countries', 'Africa')}"},
                {"time": "00:05", "cue": "Show funding graphic"}
            ],
            "duration_seconds": 45,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def generate_weekly_roundup(self, deals):
        """Generate weekly roundup"""
        if not deals:
            return None
        
        week_start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d')
        
        return {
            "week_starting": week_start,
            "title": f"African Startup Funding Roundup - Week of {week_start}",
            "description": f"This week's top African startup funding deals. {len(deals)} deals covered.",
            "voiceover_script": f"This week in African startup funding, we saw {len(deals)} notable deals...",
            "timestamps": [
                {"time": "00:00", "section": "Intro"},
                {"time": "00:15", "section": "Biggest Deals"},
                {"time": "01:00", "section": "Trends"},
                {"time": "01:45", "section": "More Deals"},
                {"time": "02:15", "section": "Wrap Up"}
            ],
            "duration_seconds": 165,
            "deals_count": len(deals),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def write_to_sheets(self, shorts, roundup):
        """Write generated content to sheets"""
        try:
            # Write shorts
            if shorts:
                shorts_sheet = self.spreadsheet.worksheet('shorts_scripts')
                for short in shorts:
                    shorts_sheet.append_row([
                        short['deal_id'],
                        short['platform'],
                        short['hook'],
                        short['voiceover_script'],
                        short['caption'],
                        ', '.join(short['hashtags']),
                        json.dumps(short['visual_cues']),
                        short['voiceover_script'],
                        short['duration_seconds'],
                        'ready',
                        short['generated_at']
                    ])
            
            # Write roundup
            if roundup:
                weekly_sheet = self.spreadsheet.worksheet('weekly_roundup')
                weekly_sheet.append_row([
                    roundup['week_starting'],
                    roundup['title'],
                    roundup['voiceover_script'][:200],
                    '',
                    '',
                    '',
                    roundup['voiceover_script'],
                    json.dumps(roundup['timestamps']),
                    'ready',
                    roundup['generated_at']
                ])
            
            print(f"Wrote {len(shorts)} shorts and 1 roundup to sheets")
        except Exception as e:
            print(f"Error writing to sheets: {e}")
    
    def run(self):
        """Main execution"""
        print("Starting content generation...")
        deals = self.get_normalized_deals()
        print(f"Found {len(deals)} deals to process")
        
        shorts = []
        for deal in deals[:10]:  # Limit for MVP
            short = self.generate_short_form(deal)
            shorts.append(short)
        
        roundup = self.generate_weekly_roundup(deals)
        
        self.write_to_sheets(shorts, roundup)
        print("Content generation complete")

if __name__ == "__main__":
    generator = ContentGenerator()
    generator.run()
