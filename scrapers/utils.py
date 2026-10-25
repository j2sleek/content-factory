#!/usr/bin/env python3
"""
Utility functions for scraping, deduplication, and normalization
"""
import hashlib
import re
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import urlparse, urlunparse

def generate_id(url: str) -> str:
    """Generate a stable ID from URL for deduplication."""
    # Normalize URL - remove tracking params
    parsed = urlparse(url)
    # Remove common tracking params
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                           parsed.params, '', ''))
    return hashlib.sha256(clean_url.encode('utf-8')).hexdigest()[:16]

def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    if not url:
        return ""
    parsed = urlparse(url)
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), 
                           parsed.params, '', ''))
    return clean_url

def extract_amount(text: str) -> Dict[str, Any]:
    """Extract funding amount from text."""
    if not text:
        return {"amount": None, "currency": None, "amount_usd": None}
    
    # Common patterns: $1M, $10 million, €2.5M, 5,000,000 USD
    patterns = [
        r'[\$€£]\s*([0-9]+(?:\.[0-9]+)?)\s*(million|billion|M|B|k|K)',
        r'([0-9]+(?:\.[0-9]+)?)\s*(million|billion)\s*(?:dollars|USD|euros|EUR)',
        r'([0-9,]+)\s*(?:USD|dollars)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num_str = match.group(1).replace(',', '')
            try:
                num = float(num_str)
                suffix = match.group(2).lower() if len(match.groups()) >= 2 else ''
                
                if suffix in ['million', 'm']:
                    amount = num * 1_000_000
                    amount_usd = amount  # Assume USD if not specified
                elif suffix in ['billion', 'b']:
                    amount = num * 1_000_000_000
                    amount_usd = amount
                elif suffix in ['k']:
                    amount = num * 1000
                    amount_usd = amount
                else:
                    amount = num
                    amount_usd = amount
                
                # Determine currency
                currency = 'USD'
                if '$' in match.group(0):
                    currency = 'USD'
                elif '€' in match.group(0):
                    currency = 'EUR'
                elif '£' in match.group(0):
                    currency = 'GBP'
                
                return {
                    "amount": amount,
                    "currency": currency,
                    "amount_usd": amount_usd,
                    "raw_match": match.group(0)
                }
            except ValueError:
                continue
    
    return {"amount": None, "currency": None, "amount_usd": None}

def extract_round(text: str) -> Optional[str]:
    """Extract funding round type."""
    if not text:
        return None
    
    rounds = [
        r'series\s+([a-z]+)', r'pre-seed', r'seed', r'series\s+a', r'series\s+b',
        r'series\s+c', r'series\s+d', r'bridge', r'convertible', r'debt', r'grant'
    ]
    
    text_lower = text.lower()
    for pattern in rounds:
        match = re.search(pattern, text_lower)
        if match:
            if match.group(0).startswith('series'):
                return f"Series {match.group(1).upper()}"
            return match.group(0).replace('-', ' ').title()
    
    return None

def extract_countries(text: str) -> list:
    """Extract African countries from text."""
    african_countries = [
        'nigeria', 'kenya', 'south africa', 'ghana', 'egypt', 'ethiopia',
        'tanzania', 'uganda', 'rwanda', 'senegal', 'ivory coast', 'côte d\'ivoire',
        'morocco', 'tunisia', 'algeria', 'cameroon', 'zimbabwe', 'zambia',
        'botswana', 'namibia', 'mozambique', 'mali', 'burkina faso', 'niger'
    ]
    
    if not text:
        return []
    
    found = []
    text_lower = text.lower()
    for country in african_countries:
        if country in text_lower:
            # Normalize name
            if country == 'côte d\'ivoire':
                found.append('Ivory Coast')
            elif country == 'ivory coast':
                found.append('Ivory Coast')
            else:
                found.append(country.title())
    
    return list(set(found))

def is_funding_related(title: str, summary: str = "", keywords: list = None) -> bool:
    """Check if article is funding related."""
    if not keywords:
        keywords = ["funding", "raise", "raised", "series", "seed", "venture", 
                   "investment", "capital", "fund", "financing", "financement"]
    
    text = f"{title} {summary}".lower()
    return any(keyword in text for keyword in keywords)

def create_deal_record(entry: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Create normalized deal record."""
    title = entry.get('title', '')
    summary = entry.get('summary', '')
    full_text = f"{title} {summary}"
    
    amount_data = extract_amount(full_text)
    round_type = extract_round(full_text)
    countries = extract_countries(full_text)
    
    return {
        "id": generate_id(entry.get('link', '')),
        "source": source,
        "title": title,
        "url": entry.get('link', ''),
        "summary": summary[:500] if summary else "",
        "published_at": entry.get('published_at') or datetime.now(timezone.utc).isoformat(),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "amount": amount_data.get('amount'),
        "currency": amount_data.get('currency'),
        "amount_usd": amount_data.get('amount_usd'),
        "round": round_type,
        "countries": ', '.join(countries) if countries else '',
        "sector": "",
        "investors": "",
        "founders": "",
        "startup_name": "",
        "use_of_funds": "",
        "tags": "",
        "status": "new",
        "processed_at": "",
        "content_generated": "false",
        "notes": ""
    }

def log_message(message: str, level: str = "INFO"):
    """Simple logging."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] [{level}] {message}")
