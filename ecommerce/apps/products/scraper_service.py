"""
Service to coordinate scraping across multiple platforms
"""
import logging
import time
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import Product, Platform, ProductPrice
from .scrapers import LazadaScraper, eBayScraper, AliExpressScraper, GeminiVisionScraper

logger = logging.getLogger(__name__)


class ScraperService:
    """Service to handle product scraping across platforms"""
    
    # Traditional CSS selector-based scrapers (fallback only)
    TRADITIONAL_SCRAPER_MAP = {
        'lazada': LazadaScraper,
        'ebay': eBayScraper,
        'aliexpress': AliExpressScraper,
    }
    
    
    @classmethod
    def get_scraper(cls, platform, use_ai=None):
        """
        Get appropriate scraper instance for a platform
        
        Args:
            platform: Platform model instance
            use_ai: Override to force AI (True) or traditional (False) scraper.
                   If None, uses settings.USE_AI_VISION_SCRAPER (default True)
            
        Returns:
            Scraper instance or None
        """
        # Check if AI vision should be used
        if use_ai is None:
            use_ai = getattr(settings, 'USE_AI_VISION_SCRAPER', True)
        
        # Use AI vision scraper if enabled and API key is configured
        if use_ai and getattr(settings, 'GOOGLE_GEMINI_API_KEY', ''):
            try:
                logger.info(f"Using AI Vision scraper for {platform.name}")
                return GeminiVisionScraper(platform, delay=platform.scraping_delay)
            except ValueError as e:
                logger.warning(f"AI Vision scraper unavailable: {e}. Falling back to traditional scraper.")
        
        # Fallback to traditional CSS selector-based scrapers
        platform_name = platform.name.lower() if platform.name else ''
        
        for key, scraper_class in cls.TRADITIONAL_SCRAPER_MAP.items():
            if key in platform_name:
                logger.info(f"Using traditional {key} scraper for {platform.name}")
                return scraper_class(platform, delay=platform.scraping_delay)
        
        logger.warning(f"No scraper found for platform: {platform.name}")
        return None
    
    @classmethod
    def scrape_product_for_platform(cls, product, platform, product_url, max_retries=3):
        """
        Scrape product price for a specific platform with retry logic
        
        Args:
            product: Product model instance
            platform: Platform model instance
            product_url: URL of the product on the platform
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            ProductPrice instance if successful, None otherwise
        """
        if not platform.is_active:
            logger.info(f"Platform {platform.name} is not active, skipping")
            return None
        
        # Validate product URL
        if not product_url or not product_url.startswith('http'):
            logger.error(f"Invalid product URL for {product.name} on {platform.name}: {product_url}")
            return None
        
        scraper = cls.get_scraper(platform)
        if not scraper:
            return None
        
        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                logger.info(f"Scraping {product.name} from {platform.name} (attempt {attempt + 1}/{max_retries})")
                data = scraper.scrape_product(product_url, product.name)
                
                if not data or data.get('price') is None:
                    logger.warning(f"No data returned for {product.name} from {platform.name}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    return None
                
                # Validate scraped data
                if not cls._validate_price_data(data, product, platform):
                    logger.error(f"Invalid price data for {product.name} from {platform.name}: {data}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    return None
                
                # Create ProductPrice record
                price_obj = ProductPrice.objects.create(
                    product=product,
                    platform=platform,
                    price=data['price'],
                    currency=data.get('currency', platform.currency or 'MYR'),
                    product_url=product_url,
                    availability=data.get('availability', 'Unknown'),
                    seller_name=data.get('seller_name', ''),
                    scraped_at=timezone.now()
                )
                
                logger.info(
                    f"Successfully scraped {product.name} from {platform.name}: "
                    f"{data['price']} {data.get('currency', 'MYR')} - {data.get('availability', 'Unknown')}"
                )
                return price_obj
                
            except Exception as e:
                logger.error(f"Error scraping {product.name} from {platform.name}: {str(e)}", exc_info=True)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} attempts failed for {product.name} from {platform.name}")
                    return None
        
        return None
    
    @classmethod
    def scrape_product(cls, product):
        """
        Scrape product prices from all active platforms
        
        Args:
            product: Product model instance
            
        Returns:
            List of ProductPrice instances created
        """
        if not product.is_active:
            logger.info(f"Product {product.name} is not active, skipping")
            return []
        
        results = []
        platforms = Platform.objects.filter(is_active=True)
        
        for platform in platforms:
            # Get product URL for this platform
            # In a real scenario, you'd store platform-specific URLs in the Product model
            # For now, we'll need to get it from existing ProductPrice records or admin input
            existing_price = ProductPrice.objects.filter(
                product=product,
                platform=platform
            ).order_by('-scraped_at').first()
            
            if existing_price and existing_price.product_url:
                product_url = existing_price.product_url
            else:
                logger.warning(f"No product URL found for {product.name} on {platform.name}")
                continue
            
            price_obj = cls.scrape_product_for_platform(product, platform, product_url)
            if price_obj:
                results.append(price_obj)
        
        return results
    
    @classmethod
    def scrape_all_products(cls):
        """
        Scrape all active products from all active platforms
        
        Returns:
            Dictionary with scraping results
        """
        products = Product.objects.filter(is_active=True)
        results = {
            'total_products': products.count(),
            'scraped_products': 0,
            'total_prices': 0,
            'errors': []
        }
        
        for product in products:
            try:
                price_objs = cls.scrape_product(product)
                if price_objs:
                    results['scraped_products'] += 1
                    results['total_prices'] += len(price_objs)
            except Exception as e:
                error_msg = f"Error scraping {product.name}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results
    
    @classmethod
    def _validate_price_data(cls, data, product, platform):
        """
        Validate scraped price data before saving
        
        Args:
            data: Dictionary containing scraped data
            product: Product model instance
            platform: Platform model instance
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            # Check required fields
            if 'price' not in data:
                logger.error("Missing 'price' field in scraped data")
                return False
            
            # Validate price
            price = data['price']
            if price is None:
                logger.error("Price is None")
                return False
            
            # Convert to Decimal and validate
            try:
                price_decimal = Decimal(str(price))
                if price_decimal <= 0:
                    logger.error(f"Invalid price value: {price} (must be > 0)")
                    return False
                if price_decimal > 999999999.99:  # Max price check
                    logger.error(f"Price too large: {price}")
                    return False
            except (ValueError, InvalidOperation) as e:
                logger.error(f"Failed to convert price to Decimal: {price} - {e}")
                return False
            
            # Validate currency
            currency = data.get('currency', platform.currency or 'MYR')
            if not currency or len(currency) > 10:
                logger.error(f"Invalid currency: {currency}")
                return False
            
            # Validate availability (if present)
            availability = data.get('availability', '')
            if availability and len(availability) > 50:
                logger.warning(f"Availability text too long, will be truncated: {availability}")
            
            # Validate seller name (if present)
            seller_name = data.get('seller_name', '')
            if seller_name and len(seller_name) > 200:
                logger.warning(f"Seller name too long, will be truncated: {seller_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating price data: {e}", exc_info=True)
            return False

