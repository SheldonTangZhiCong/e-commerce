import logging
import json
from decimal import Decimal
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class eBayScraper(BaseScraper):
    """Scraper for eBay Australia platform"""
    
    def scrape_product(self, product_url, product_name=None):
        """
        Scrape product from eBay Australia
        
        Uses Playwright to handle JavaScript-rendered pricing
        """
        try:
            html = self.get_page_html(product_url)
            if not html:
                return None
            
            soup = self.parse_html(html)
            
            # Try to extract from JSON-LD structured data (most reliable)
            price_value = None
            currency = 'AUD'  # Default for eBay Australia
            
            # Look for JSON-LD script tag
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'offers' in data:
                        offers = data['offers']
                        if isinstance(offers, dict):
                            price_value = offers.get('price')
                            currency = offers.get('priceCurrency', 'AUD')
                        break
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            # Fallback: Try common eBay price selectors
            if not price_value:
                # Try main price element
                price_element = soup.find('span', class_='ux-textspans') or \
                               soup.find('div', {'itemprop': 'price'}) or \
                               soup.find('span', {'class': 'display-price'})
                
                if price_element:
                    price_text = price_element.get_text().strip()
                    price_value = self.extract_price(price_text)
            
            if not price_value:
                logger.warning(f"Could not extract price from eBay URL: {product_url}")
                return None
            
            # Extract seller name
            seller_name = 'eBay Seller'
            seller_element = soup.find('span', class_='ux-seller-section__item--seller') or \
                            soup.find('a', class_='seller-persona')
            if seller_element:
                seller_name = seller_element.get_text().strip()
            
            # Availability - look for "in stock" or "available" indicators
            availability = 'Unknown'
            availability_element = soup.find('div', class_='d-quantity__availability') or \
                                  soup.find('span', class_='ux-qty')
            if availability_element:
                avail_text = availability_element.get_text().lower()
                if 'available' in avail_text or 'in stock' in avail_text:
                    availability = 'In Stock'
                elif 'out of stock' in avail_text or 'sold out' in avail_text:
                    availability = 'Out of Stock'
            
            return {
                'price': Decimal(str(price_value)),
                'currency': currency,
                'availability': availability,
                'seller_name': seller_name,
                'product_url': product_url
            }
            
        except Exception as e:
            logger.error(f"Error scraping eBay product: {e}")
            return None