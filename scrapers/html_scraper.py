#!/usr/bin/env python3
"""
HTML Scraper Fallback for sites without RSS
"""
import requests
from bs4 import BeautifulSoup
import yaml
from datetime import datetime, timezone
from typing import List, Dict, Any

from .utils import create_deal_record, is_funding_related, log_message, normalize_url

class HTMLScraper:
    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def load_config(self) -> Dict:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            log_message(f"Error loading config: {e}", "ERROR")
            return {"html_sources": []}
    
    def scrape_source(self, source_config: Dict) -> List[Dict[str, Any]]:
        source_name = source_config['name']
        url = source_config['url']
        selectors = source_config.get('selectors', {})
        
        log_message(f"Scraping HTML source: {source_name}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.select(selectors.get('articles', 'article'))
            
            deals = []
            for article in articles:
                title_elem = article.select_one(selectors.get('title', 'h2 a'))
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link = title_elem.get('href', '')
                if link and not link.startswith('http'):
                    from urllib.parse import urljoin
                    link = urljoin(url, link)
                
                summary_elem = article.select_one(selectors.get('summary', 'p'))
                summary = summary_elem.get_text(strip=True) if summary_elem else ""
                
                if not is_funding_related(title, summary):
                    continue
                
                entry_data = {
                    'title': title,
                    'summary': summary,
                    'link': normalize_url(link),
                    'published_at': datetime.now(timezone.utc).isoformat()
                }
                
                deal = create_deal_record(entry_data, source_name)
                deals.append(deal)
            
            log_message(f"Found {len(deals)} items from {source_name}")
            return deals
            
        except Exception as e:
            log_message(f"Error scraping {source_name}: {e}", "ERROR")
            return []
    
    def scrape_all(self) -> List[Dict[str, Any]]:
        all_deals = []
        sources = self.config.get('html_sources', [])
        
        for source_config in sources:
            if not source_config.get('enabled', True):
                continue
            try:
                deals = self.scrape_source(source_config)
                all_deals.extend(deals)
            except Exception as e:
                log_message(f"Failed to scrape {source_config['name']}: {e}", "ERROR")
        
        return all_deals
