import logging
import json
from decimal import Decimal
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AliExpressScraper(BaseScraper):
    """Scraper for AliExpress platform"""
    
    def scrape_product(self, product_url, product_name=None):
        """
        Scrape product from AliExpress
        
        Uses Playwright to handle JavaScript-heavy page rendering
        """
        try:
            html = self.get_page_html(product_url)
            if not html:
                return None
            
            soup = self.parse_html(html)
            
            price_value = None
            currency = 'USD'  # Default for AliExpress
            
            # Try to extract from window.runParams JSON data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'window.runParams' in script.string:
                    try:
                        # Extract JSON data from script
                        import re
                        match = re.search(r'data:\s*({.*?})\s*};', script.string, re.DOTALL)
                        if match:
                            data = json.loads(match.group(1))
                            
                            # Try to find price in various locations
                            price_info = data.get('priceModule', {})
                            if price_info:
                                price_value = price_info.get('minActivityAmount', {}).get('value') or \
                                             price_info.get('minAmount', {}).get('value')
                                currency_info = price_info.get('minActivityAmount', {}).get('currency') or \
                                               price_info.get('minAmount', {}).get('currency', 'USD')
                                currency = currency_info
                                break
                    except (json.JSONDecodeError, AttributeError, KeyError):
                        continue
            
            # Fallback: Try common price selectors
            if not price_value:
                price_element = soup.find('span', class_='product-price-value') or \
                               soup.find('span', {'itemprop': 'price'}) or \
                               soup.find('div', class_='product-price')
                
                if price_element:
                    price_text = price_element.get_text().strip()
                    price_value = self.extract_price(price_text)
                    
                    # Extract currency from symbol
                    if '$' in price_element.get_text():
                        currency = 'USD'
                    elif '€' in price_element.get_text():
                        currency = 'EUR'
            
            if not price_value:
                logger.warning(f"Could not extract price from AliExpress URL: {product_url}")
                return None
            
            # Extract seller/store name
            seller_name = 'AliExpress Store'
            seller_element = soup.find('a', class_='shop-name') or \
                            soup.find('span', {'class': 'shop-name'})
            if seller_element:
                seller_name = seller_element.get_text().strip()
            
            # Availability
            availability = 'In Stock'  # AliExpress usually shows in stock
            stock_element = soup.find('span', class_='product-quantity-info')
            if stock_element:
                stock_text = stock_element.get_text().lower()
                if 'out of stock' in stock_text or 'sold out' in stock_text:
                    availability = 'Out of Stock'
                elif 'only' in stock_text and 'left' in stock_text:
                    availability = 'Limited Stock'
            
            return {
                'price': Decimal(str(price_value)),
                'currency': currency,
                'availability': availability,
                'seller_name': seller_name,
                'product_url': product_url
            }
            
        except Exception as e:
            logger.error(f"Error scraping AliExpress product: {e}")
            return None
