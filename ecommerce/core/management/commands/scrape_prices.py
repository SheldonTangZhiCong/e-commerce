"""
Management command to scrape product prices from all platforms
"""
from django.core.management.base import BaseCommand
from apps.products.scraper_service import ScraperService
from apps.products.models import Product
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape product prices from all active platforms'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-id',
            type=int,
            help='Scrape only a specific product by ID',
        )
        parser.add_argument(
            '--product-slug',
            type=str,
            help='Scrape only a specific product by slug',
        )
        parser.add_argument(
            '--platform',
            type=str,
            help='Scrape only from a specific platform (e.g., "Shopee", "Lazada")',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test scraping without saving to database',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting price scraping...'))
        
        product_id = options.get('product_id')
        product_slug = options.get('product_slug')
        platform_filter = options.get('platform')
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))
        
        # Single product scraping
        if product_id:
            try:
                product = Product.objects.get(id=product_id, is_active=True)
                self._scrape_single_product(product, platform_filter, dry_run)
            except Product.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Product with ID {product_id} not found')
                )
                return
        
        elif product_slug:
            try:
                product = Product.objects.get(slug=product_slug, is_active=True)
                self._scrape_single_product(product, platform_filter, dry_run)
            except Product.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Product with slug {product_slug} not found')
                )
                return
        
        else:
            # Scrape all products
            self._scrape_all_products(platform_filter, dry_run)
    
    def _scrape_single_product(self, product, platform_filter=None, dry_run=False):
        """Scrape a single product with optional platform filter"""
        self.stdout.write(f'Scraping product: {product.name}')
        
        from apps.products.models import Platform, ProductPrice
        
        # Get platforms to scrape
        if platform_filter:
            platforms = Platform.objects.filter(name__icontains=platform_filter, is_active=True)
            if not platforms.exists():
                self.stdout.write(self.style.ERROR(f'No active platform found matching "{platform_filter}"'))
                return
        else:
            platforms = Platform.objects.filter(is_active=True)
        
        success_count = 0
        for platform in platforms:
            # Get product URL
            existing_price = ProductPrice.objects.filter(
                product=product,
                platform=platform
            ).order_by('-scraped_at').first()
            
            if not existing_price or not existing_price.product_url:
                self.stdout.write(
                    self.style.WARNING(f'  No URL found for {platform.name}, skipping')
                )
                continue
            
            self.stdout.write(f'  Scraping from {platform.name}...')
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'    [DRY RUN] Would scrape: {existing_price.product_url}'))
                continue
            
            price_obj = ScraperService.scrape_product_for_platform(
                product, platform, existing_price.product_url
            )
            
            if price_obj:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'    ✓ {price_obj.currency} {price_obj.price} - {price_obj.availability}'
                    )
                )
                success_count += 1
            else:
                self.stdout.write(self.style.ERROR(f'    ✗ Failed'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted: {success_count}/{platforms.count()} platforms scraped successfully'
            )
        )
    
    def _scrape_all_products(self, platform_filter=None, dry_run=False):
        """Scrape all active products with optional platform filter"""
        from apps.products.models import Product
        
        products = Product.objects.filter(is_active=True)
        total_products = products.count()
        
        if total_products == 0:
            self.stdout.write(self.style.WARNING('No active products found'))
            return
        
        self.stdout.write(f'Found {total_products} active products\n')
        
        results = {
            'total_products': total_products,
            'scraped_products': 0,
            'total_prices': 0,
            'errors': []
        }
        
        for idx, product in enumerate(products, 1):
            self.stdout.write(f'[{idx}/{total_products}] {product.name}')
            
            if dry_run:
                self.stdout.write(self.style.WARNING('  [DRY RUN] Skipping actual scrape'))
                continue
            
            try:
                # If platform filter is specified, scrape only that platform
                if platform_filter:
                    self._scrape_single_product(product, platform_filter, dry_run=False)
                else:
                    price_objs = ScraperService.scrape_product(product)
                    if price_objs:
                        results['scraped_products'] += 1
                        results['total_prices'] += len(price_objs)
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Scraped {len(price_objs)} prices')
                        )
                    else:
                        self.stdout.write(self.style.WARNING('  No prices scraped'))
            except Exception as e:
                error_msg = f'{product.name}: {str(e)}'
                logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
        
        # Print summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('SCRAPING SUMMARY'))
        self.stdout.write('='*50)
        self.stdout.write(f'Total products: {results["total_products"]}')
        self.stdout.write(f'Scraped successfully: {results["scraped_products"]}')
        self.stdout.write(f'Total prices collected: {results["total_prices"]}')
        
        if results['errors']:
            self.stdout.write('\n' + self.style.WARNING(f'Errors encountered ({len(results["errors"])}):'))
            for error in results['errors']:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        else:
            self.stdout.write('\n' + self.style.SUCCESS('No errors! 🎉'))

