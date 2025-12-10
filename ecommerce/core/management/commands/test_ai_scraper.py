"""
Test management command to verify AI vision scraper setup
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import google.generativeai as genai
from playwright.sync_api import sync_playwright


class Command(BaseCommand):
    help = 'Test Google Gemini AI Vision scraper setup'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Testing AI Vision Scraper Setup...\n'))
        
        # 1. Check API Key
        api_key = settings.GOOGLE_GEMINI_API_KEY
        if not api_key:
            self.stdout.write(self.style.ERROR('❌ GOOGLE_GEMINI_API_KEY not configured!'))
            self.stdout.write('   Set it in settings.py or environment variable')
            return
        
        self.stdout.write(self.style.SUCCESS(f'✓ API Key configured: {api_key[:10]}...'))
        
        # 2. Test Gemini API Connection
        try:
            genai.configure(api_key=api_key)
            
            # List available models
            self.stdout.write('\n📋 Available Gemini models:')
            try:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        self.stdout.write(f'   - {m.name}')
            except Exception as e:
                self.stdout.write(f'   Could not list models: {e}')
            
            # Test with gemini-flash-latest (or fallback to gemini-1.5-pro)
            try:
                model = genai.GenerativeModel('gemini-flash-latest')
                self.stdout.write('\n✓ Using model: gemini-flash-latest')
            except:
                try:
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    self.stdout.write('\n✓ Using model: gemini-1.5-pro (fallback)')
                except:
                    model = genai.GenerativeModel('gemini-pro-vision')
                    self.stdout.write('\n✓ Using model: gemini-pro-vision (fallback 2)')
            
            # Simple test prompt
            response = model.generate_content("Say 'Hello! API is working!'")
            self.stdout.write(self.style.SUCCESS(f'✓ Gemini API connected successfully'))
            self.stdout.write(f'  Response: {response.text}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Gemini API test failed: {e}'))
            return
        
        # 3. Check Playwright
        try:
            self.stdout.write(self.style.SUCCESS('✓ Playwright imported successfully'))
            
            # Test browser launch
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                self.stdout.write(self.style.SUCCESS('✓ Chromium browser launched successfully'))
                browser.close()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Playwright test failed: {e}'))
            self.stdout.write('   Run: playwright install chromium')
            return
        
        # 4. Check Settings
        self.stdout.write('\n📋 Current Settings:')
        self.stdout.write(f'   USE_AI_VISION_SCRAPER: {settings.USE_AI_VISION_SCRAPER}')
        self.stdout.write(f'   AI_SCRAPER_MAX_RETRIES: {settings.AI_SCRAPER_MAX_RETRIES}')
        
        # 5. Check Database
        from apps.products.models import Product, Platform, ProductPrice
        
        platforms_count = Platform.objects.filter(is_active=True).count()
        products_count = Product.objects.filter(is_active=True).count()
        prices_with_urls = ProductPrice.objects.exclude(product_url='').count()
        
        self.stdout.write('\n📊 Database Status:')
        self.stdout.write(f'   Active Platforms: {platforms_count}')
        self.stdout.write(f'   Active Products: {products_count}')
        self.stdout.write(f'   Product URLs configured: {prices_with_urls}')
        
        if platforms_count == 0:
            self.stdout.write(self.style.WARNING('\n⚠ No platforms configured!'))
            self.stdout.write('   Add platforms via admin: http://127.0.0.1:8000/admin/products/platform/add/')
        
        if products_count == 0:
            self.stdout.write(self.style.WARNING('\n⚠ No products configured!'))
            self.stdout.write('   Add products via admin: http://127.0.0.1:8000/admin/products/product/add/')
        
        if prices_with_urls == 0:
            self.stdout.write(self.style.WARNING('\n⚠ No product URLs configured!'))
            self.stdout.write('   Add product URLs via admin: http://127.0.0.1:8000/admin/products/productprice/add/')
            self.stdout.write('   The scraper needs URLs to know which pages to scrape!')
        
        # Summary
        self.stdout.write('\n' + '='*60)
        if platforms_count > 0 and products_count > 0 and prices_with_urls > 0:
            self.stdout.write(self.style.SUCCESS('✅ Setup Complete! Ready to scrape.'))
            self.stdout.write('\nNext step: Run scraper with:')
            self.stdout.write(self.style.SUCCESS('  python manage.py scrape_prices'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Setup incomplete. Please add data via admin panel.'))
            self.stdout.write('\nSteps:')
            self.stdout.write('  1. Add platforms (Shopee, Lazada, etc.)')
            self.stdout.write('  2. Add products to track')
            self.stdout.write('  3. Add product URLs for each platform')
            self.stdout.write('  4. Run: python manage.py scrape_prices')
        
        self.stdout.write('='*60)
