"""
Base scraper class for all e-commerce platform scrapers
"""
import time
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import datetime
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all e-commerce platform scrapers using Playwright"""
    
    def __init__(self, platform, delay=2):
        """
        Initialize scraper
        
        Args:
            platform: Platform model instance
            delay: Delay between requests in seconds
        """
        self.platform = platform
        self.delay = delay
    
    @abstractmethod
    def scrape_product(self, product_url, product_name=None):
        """
        Scrape product information from a URL
        
        Args:
            product_url: URL of the product page
            product_name: Optional product name for validation
            
        Returns:
            dict with keys: price, currency, availability, seller_name, product_url
        """
        pass
    
    def extract_price(self, text):
        """
        Extract numeric price from text
        
        Args:
            text: Text containing price
            
        Returns:
            Decimal price value
        """
        if not text:
            return None
        
        # Remove common currency symbols and whitespace
        import re
        # Remove all non-digit characters except decimal point
        price_str = re.sub(r'[^\d.]', '', str(text))
        try:
            return Decimal(price_str)
        except (ValueError, TypeError):
            logger.warning(f"Could not extract price from: {text}")
            return None
    
    def get_page_html(self, url, max_retries=3):
        """
        Get rendered HTML using Playwright (supports JavaScript)
        
        Args:
            url: URL to request
            max_retries: Maximum number of retry attempts
            
        Returns:
            HTML string or None
        """
        for attempt in range(max_retries):
            try:
                time.sleep(self.delay)
                
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )
                    page = context.new_page()
                    
                    # Navigate and wait for content
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    page.wait_for_timeout(3000)  # Wait for JavaScript to execute
                    
                    # Get rendered HTML
                    html = page.content()
                    
                    browser.close()
                    return html
                    
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.delay * (attempt + 1))
                else:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
        
        return None
    
    def parse_html(self, html_content):
        """Parse HTML content using BeautifulSoup"""
        from bs4 import BeautifulSoup
        return BeautifulSoup(html_content, 'html.parser')


