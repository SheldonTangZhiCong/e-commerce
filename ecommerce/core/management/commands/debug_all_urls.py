"""
Enhanced debug command that automatically saves screenshots
"""
from django.core.management.base import BaseCommand
from apps.products.models import ProductPrice
from apps.products.scrapers import GeminiVisionScraper
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Debug all product URLs and save screenshots'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🔍 Debugging All Product URLs...\n'))
        
        # Get all product prices with URLs
        product_prices = ProductPrice.objects.exclude(product_url='').select_related('product', 'platform')
        
        if not product_prices.exists():
            self.stdout.write(self.style.ERROR('❌ No product URLs found!'))
            return
        
        from django.conf import settings
        screenshot_dir = Path(settings.MEDIA_ROOT) / 'debug_screenshots'
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        for pp in product_prices:
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(f'Product: {pp.product.name}')
            self.stdout.write(f'Platform: {pp.platform.name}')
            self.stdout.write(f'URL: {pp.product_url[:100]}...')
            
            try:
                # Initialize scraper
                scraper = GeminiVisionScraper(pp.platform, delay=2)
                
                # Take screenshot
                self.stdout.write('\n📸 Taking screenshot...')
                screenshot_bytes = scraper._take_screenshot(pp.product_url)
                
                if screenshot_bytes:
                    # Save screenshot
                    filename = f"{pp.platform.name.lower()}_{pp.product.slug or 'product'}.png"
                    filepath = screenshot_dir / filename
                    
                    with open(filepath, 'wb') as f:
                        f.write(screenshot_bytes)
                    
                    self.stdout.write(self.style.SUCCESS(f'✓ Screenshot saved: {filepath}'))
                    self.stdout.write(f'   Size: {len(screenshot_bytes)} bytes')
                    
                    # Try AI extraction
                    self.stdout.write('\n🤖 Testing AI extraction...')
                    price_data = scraper._extract_price_with_ai(screenshot_bytes, pp.product.name)
                    
                    if price_data and price_data.get('price'):
                        self.stdout.write(self.style.SUCCESS('✓ AI extraction successful!'))
                        self.stdout.write(f'   Price: {price_data.get("price")} {price_data.get("currency")}')
                        self.stdout.write(f'   Availability: {price_data.get("availability")}')
                        self.stdout.write(f'   Seller: {price_data.get("seller_name")}')
                    else:
                        self.stdout.write(self.style.ERROR('❌ AI could not extract price'))
                        self.stdout.write(f'   Response: {price_data}')
                        self.stdout.write(f'\n⚠️  Check screenshot: {filepath}')
                        self.stdout.write('   It might show:')
                        self.stdout.write('   - CAPTCHA or login page')
                        self.stdout.write('   - "Access Denied" or bot detection')
                        self.stdout.write('   - Incomplete page load (blank/loading)')
                else:
                    self.stdout.write(self.style.ERROR('❌ Failed to capture screenshot'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
                import traceback
                traceback.print_exc()
        
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS(f'\n✅ Screenshots saved to: {screenshot_dir}'))
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Open the screenshot files to see what the browser captured')
        self.stdout.write('2. If you see CAPTCHA/login - the site is blocking bots')
        self.stdout.write('3. If you see blank page - increase wait time')
        self.stdout.write('4. If you see the product correctly - improve AI prompt')
