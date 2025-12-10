"""
Lazada scraper implementation
"""
import logging
from decimal import Decimal
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class LazadaScraper(BaseScraper):
    """Scraper for Lazada platform"""
    
    def scrape_product(self, product_url, product_name=None):
        """
        Scrape product from Lazada
        
        Uses Playwright to handle JavaScript-rendered prices
        """
        try:
            html = self.get_page_html(product_url)
            if not html:
                return None
            
            soup = self.parse_html(html)
            
            # Price is in the span with class 'pdp-price_type_normal'
            price_element = soup.find('span', class_='pdp-price_type_normal') or \
                           soup.find('span', class_='pdp-product-price') or \
                           soup.find('span', {'class': 'price'})
            
            # Currency element
            currency_element = soup.find('span', class_='pdp-price_currency')
            
            if not price_element:
                logger.warning(f"Could not extract price from Lazada URL: {product_url} (Selector not found)")
                return None
            
            price_text = price_element.get_text().strip()
            price_value = self.extract_price(price_text)
            
            currency = 'MYR'  # Default for Lazada MY
            if currency_element and 'RM' in currency_element.get_text():
                currency = 'MYR'
            
            # Extract availability
            availability = 'In Stock'
            stock_element = soup.find('div', class_='stock-status') or \
                          soup.find('span', class_='stock')
            if stock_element:
                stock_text = stock_element.get_text().lower()
                if 'out of stock' in stock_text or 'sold out' in stock_text:
                    availability = 'Out of Stock'
            
            # Extract seller name
            seller_name = ''
            seller_element = soup.find('a', class_='seller-name') or \
                          soup.find('div', class_='seller-info')
            if seller_element:
                seller_name = seller_element.get_text().strip()
            
            return {
                'price': price_value,
                'currency': 'MYR',
                'availability': availability,
                'seller_name': seller_name,
                'product_url': product_url
            }
            
        except Exception as e:
            logger.error(f"Error scraping Lazada product: {e}")
            return None
