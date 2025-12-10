"""
AI Vision-based scraper using Google Gemini
Works for all e-commerce platforms without CSS selectors
"""
import os
import logging
import base64
import json
from pathlib import Path
from decimal import Decimal
from io import BytesIO
from PIL import Image

import google.generativeai as genai
from playwright.sync_api import sync_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GeminiVisionScraper(BaseScraper):
    """Universal scraper using Google Gemini Vision API"""
    
    def __init__(self, platform, delay=2, api_key=None):
        super().__init__(platform, delay)
        
        # Get API key from settings or parameter
        from django.conf import settings
        self.api_key = api_key or getattr(settings, 'GOOGLE_GEMINI_API_KEY', '')
        
        if not self.api_key:
            raise ValueError("Google Gemini API key not configured. Get one at https://aistudio.google.com/app/apikey")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        # Use gemini-flash-latest (free tier: 50 requests/day) or gemini-pro (older, more available)
        # Try gemini-flash-latest first, fallback to gemini-pro if not available
        try:
            self.model = genai.GenerativeModel('gemini-flash-latest')
        except:
            self.model = genai.GenerativeModel('gemini-1.5-pro')  # Fallback for vision tasks

    def scrape_product(self, product_url, product_name=None):
        """
        Scrape product using AI vision
        
        Args:
            product_url: URL of the product page
            product_name: Optional product name for validation
            
        Returns:
            dict with keys: price, currency, availability, seller_name, product_url
        """
        try:
            logger.info(f"Starting AI vision scraping for: {product_url}")
            
            # 1. Take screenshot of product page
            screenshot_bytes = self._take_screenshot(product_url)
            if not screenshot_bytes:
                logger.error(f"Failed to capture screenshot for: {product_url}")
                return None
            
            # 2. Extract price using Gemini Vision
            price_data = self._extract_price_with_ai(screenshot_bytes, product_name)
            if not price_data:
                logger.error(f"Failed to extract price from screenshot for: {product_url}")
                return None
            
            # 3. Add product URL to result
            price_data['product_url'] = product_url
            
            logger.info(f"Successfully scraped {product_name or 'product'}: {price_data.get('price')} {price_data.get('currency')}")
            return price_data
            
        except Exception as e:
            logger.error(f"Error in AI vision scraping: {e}", exc_info=True)
            return None
    
    def _take_screenshot(self, url, max_retries=2):
        """
        Take screenshot of product page using Playwright
        
        Args:
            url: Product page URL
            max_retries: Number of retry attempts
            
        Returns:
            Screenshot as bytes or None
        """
        for attempt in range(max_retries):
            try:
                with sync_playwright() as p:
                    # Launch browser (headless mode)
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        viewport={'width': 1280, 'height': 1024},  # Increased height to capture more content
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        locale='en-MY'  # Set locale to bypass language selection
                    )
                    
                    # Add cookies for Shopee to bypass language selection
                    if 'shopee' in url.lower():
                        context.add_cookies([
                            {'name': 'SPC_F', 'value': 'en', 'domain': '.shopee.com.my', 'path': '/'},
                            {'name': 'language', 'value': 'en', 'domain': '.shopee.com.my', 'path': '/'},
                        ])
                        logger.info("Added Shopee language cookies")
                    
                    page = context.new_page()
                    
                    # Navigate to product page
                    logger.info(f"Loading page: {url}")
                    try:
                        page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        logger.info("Page loaded, waiting for content to render...")
                    except Exception as goto_error:
                        logger.error(f"Page navigation failed: {goto_error}")
                        raise
                    
                    # Wait for page to fully load (give time for prices to render)
                    # Increased from 3 to 5 seconds for sites with heavy JS
                    page.wait_for_timeout(5000)  # 5 seconds
                    
                    # Take screenshot
                    screenshot_bytes = page.screenshot(full_page=False, type='png')
                    
                    browser.close()
                    
                    logger.info(f"Screenshot captured: {len(screenshot_bytes)} bytes")
                    return screenshot_bytes
                    
            except Exception as e:
                logger.error(f"Screenshot attempt {attempt + 1} failed: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(self.delay * (attempt + 1))
                else:
                    logger.error(f"Failed to capture screenshot after {max_retries} attempts")
                    logger.error(f"Last error: {e}", exc_info=True)
                    return None
    
    def _extract_price_with_ai(self, screenshot_bytes, product_name=None):
        """
        Extract price data from screenshot using Gemini Vision
        
        Args:
            screenshot_bytes: Screenshot as bytes
            product_name: Optional product name for context
            
        Returns:
            dict with price, currency, availability, seller_name
        """
        response_text = None
        try:
            # Convert screenshot to PIL Image
            image = Image.open(BytesIO(screenshot_bytes))
            
            # Create prompt for Gemini
            product_context = f" for product '{product_name}'" if product_name else ""
            prompt = f"""
You are analyzing a product page screenshot{product_context}.

Extract the following information and return it as valid JSON:

1. "price": The current/sale price as a decimal number (e.g., 5499.00). Look for the main SALE price or CURRENT price, NOT the original/crossed-out price. This is usually the largest price displayed.

2. "currency": The currency code (e.g., "MYR", "RM", "USD", "AUD", "CNY", "SGD", "EUR", "GBP")

3. "availability": Stock status - this is VERY IMPORTANT. Look carefully for stock information, which is typically located:
   - Directly BELOW the price
   - Near "Add to Cart" or "Buy Now" button
   - In a box or highlighted section
   
   Return ONE of these values based on what you see:
   - "In Stock" - if you see: "In Stock", "Available", "X units available", "X left", "Ready to Ship", "Ships Today"
   - "Out of Stock" - if you see: "Out of Stock", "Sold Out", "Unavailable", "Currently Unavailable", "Notify Me", "Email When Available"
   - "Pre-Order" - if you see: "Pre-Order", "Coming Soon", "Available for Pre-Order"
   - "Limited Stock" - if you see: "Only X left", "Limited Quantity", "Low Stock", "Hurry, X remaining"
   - "Unknown" - if you cannot find any stock information
   
   IMPORTANT: Look carefully near the price and product title. On eBay, stock status is usually below the price.

4. "seller_name": The shop/seller name if visible (e.g., "Official Store", "Apple Flagship Store", seller username on eBay)

5. "quantity_available": (OPTIONAL) If you can see a specific number like "5 units left" or "Only 3 remaining", extract that number. Otherwise set to null.

Important Guidelines:
- Return ONLY valid JSON, no other text or explanations
- If you cannot find a value, use null (except availability should be "Unknown")
- Price should be a number without currency symbols or commas
- Look for the prominent sale/current price, ignore original/strikethrough prices
- Stock status is critical - look thoroughly near the price section
- Be specific about availability based on the exact text you see

Example response format:
{{"price": 5499.00, "currency": "MYR", "availability": "In Stock", "seller_name": "Official Store", "quantity_available": null}}

Another example (eBay):
{{"price": 1299.99, "currency": "AUD", "availability": "Limited Stock", "seller_name": "tech_seller_au", "quantity_available": 3}}

Now analyze this product page carefully:
"""
            
            # Call Gemini Vision API
            logger.info("Calling Gemini Vision API...")
            response = self.model.generate_content([prompt, image])
            
            # Parse response
            response_text = response.text.strip()
            logger.info(f"Gemini raw response: {response_text}")
            
            # Extract JSON from response (handle markdown code blocks)
            json_str = response_text
            if '```json' in response_text:
                json_str = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                json_str = response_text.split('```')[1].split('```')[0].strip()
            
            logger.info(f"Extracted JSON string: {json_str}")
            
            # Parse JSON
            try:
                data = json.loads(json_str)
                logger.info(f"Parsed data: {data}")
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON parsing failed: {json_err}")
                logger.error(f"Attempted to parse: {json_str}")
                return None
            
            # Check if price was found
            if not data.get('price') or data.get('price') is None:
                logger.error(f"AI could not find price in screenshot")
                logger.error(f"Full AI response: {data}")
                return None
            
            # Convert price to Decimal
            try:
                data['price'] = Decimal(str(data['price']))
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to convert price to Decimal: {e}")
                logger.error(f"Price value was: {data.get('price')}")
                return None
            
            # Set defaults for optional fields
            if not data.get('currency'):
                data['currency'] = self.platform.currency or 'MYR'
            if not data.get('availability'):
                data['availability'] = 'Unknown'
            if not data.get('seller_name'):
                data['seller_name'] = ''
            if not data.get('quantity_available'):
                data['quantity_available'] = None
            
            logger.info(f"Successfully extracted price data: {data}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Response was: {response_text}")
            # Save problematic response for debugging
            try:
                import os
                from django.conf import settings
                debug_dir = os.path.join(settings.BASE_DIR, 'logs', 'ai_debug')
                os.makedirs(debug_dir, exist_ok=True)
                
                debug_file = os.path.join(debug_dir, f'failed_response_{product_name or "unknown"}.txt')
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"Raw response:\n{response_text}\n\n")
                    f.write(f"Attempted JSON:\n{json_str if 'json_str' in locals() else 'N/A'}\n")
                logger.info(f"Saved debug info to: {debug_file}")
            except:
                pass
            return None
        except Exception as e:
            logger.error(f"Error extracting price with AI: {e}", exc_info=True)
            if response_text:
                logger.error(f"Last AI response: {response_text}")
            return None
