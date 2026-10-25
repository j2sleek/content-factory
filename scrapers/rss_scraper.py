#!/usr/bin/env python3
"""
RSS Feed Scraper for African Startup Funding News
"""
import feedparser
import yaml
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests

from .utils import create_deal_record, is_funding_related, log_message, normalize_url

class RSScraper:
    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ContentFactory/1.0; +https://github.com/content-factory)'
        })
    
    def load_config(self) -> Dict:
        """Load configuration from YAML."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            log_message(f"Error loading config: {e}", "ERROR")
            return {"rss_feeds": [], "filters": {}}
    
    def scrape_feed(self, feed_config: Dict) -> List[Dict[str, Any]]:
        """Scrape a single RSS feed."""
        feed_name = feed_config['name']
        feed_url = feed_config['url']
        keywords = feed_config.get('funding_keywords', [])
        
        log_message(f"Scraping RSS feed: {feed_name}")
        
        try:
            # Parse feed
            feed = feedparser.parse(feed_url)
            
            if feed.bozo and feed.bozo_exception:
                log_message(f"Feed parsing warning for {feed_name}: {feed.bozo_exception}", "WARNING")
            
            deals = []
            for entry in feed.entries:
                title = entry.get('title', '')
                summary = entry.get('summary', '') or entry.get('description', '')
                link = entry.get('link', '')
                
                if not title or not link:
                    continue
                
                # Check if funding related
                if self.config.get('filters', {}).get('require_funding_keywords', True):
                    if not is_funding_related(title, summary, keywords):
                        continue
                
                # Extract published date
                published_at = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        published_at = dt.isoformat()
                    except:
                        pass
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    try:
                        dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                        published_at = dt.isoformat()
                    except:
                        pass
                
                entry_data = {
                    'title': title,
                    'summary': summary,
                    'link': normalize_url(link),
                    'published_at': published_at
                }
                
                deal = create_deal_record(entry_data, feed_name)
                deals.append(deal)
            
            log_message(f"Found {len(deals)} funding-related items from {feed_name}")
            return deals
            
        except Exception as e:
            log_message(f"Error scraping {feed_name}: {e}", "ERROR")
            return []
    
    def scrape_all(self) -> List[Dict[str, Any]]:
        """Scrape all enabled RSS feeds."""
        all_deals = []
        feeds = self.config.get('rss_feeds', [])
        
        for feed_config in feeds:
            if not feed_config.get('enabled', True):
                continue
            
            try:
                deals = self.scrape_feed(feed_config)
                all_deals.extend(deals)
            except Exception as e:
                log_message(f"Failed to scrape {feed_config['name']}: {e}", "ERROR")
                continue
        
        log_message(f"Total deals scraped: {len(all_deals)}")
        return all_deals
    
    def save_to_file(self, deals: List[Dict[str, Any]], filename: str = None):
        """Save deals to JSON file for testing."""
        if not filename:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"scraped_deals_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(deals, f, indent=2, ensure_ascii=False)
        
        log_message(f"Saved {len(deals)} deals to {filename}")

if __name__ == "__main__":
    scraper = RSScraper()
    deals = scraper.scrape_all()
    scraper.save_to_file(deals)
    print(json.dumps(deals[:2], indent=2))
