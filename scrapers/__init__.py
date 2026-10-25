"""Scrapers module for African startup funding news."""
from .rss_scraper import RSScraper
from .html_scraper import HTMLScraper
from .utils import *

__all__ = ['RSScraper', 'HTMLScraper']
