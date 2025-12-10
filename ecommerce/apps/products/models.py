from unidecode import unidecode

from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from core.abstract_models import TimeStampedModel
from core.utils import generate_thumbnail, generate_sha1
from sorl.thumbnail import ImageField

def _generate_product_image(instance, filename):
    extension = filename.split('.')[-1].lower()
    # Use filename as identifier if instance.id is None (new object)
    identifier = instance.id if instance.id else filename
    salt, hash_key = generate_sha1(identifier)
    # Use slug if available, otherwise use 'product'
    name = instance.slug if instance.slug else 'product'
    return 'products/product_image/%(name)s/%(hash)s.%(extension)s' % {
        'name': name, 'hash': hash_key[:10], 'extension': extension
    }

class Platform(TimeStampedModel):
    """E-commerce platform (Shopee, Lazada, Amazon, etc.)"""
    
    name = models.CharField(max_length=100, unique=True, help_text="Platform name (e.g., Shopee, Lazada)", blank=True, null=True)
    base_url = models.URLField(help_text="Base URL for the platform", blank=True, null=True)
    currency = models.CharField(max_length=10, default='MYR', help_text="Default currency code", blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Whether to scrape this platform")
    
    # Scraping configuration (optional, for future use)
    scraping_delay = models.PositiveIntegerField(default=2, help_text="Delay between requests in seconds")
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Platform'
        verbose_name_plural = 'Platforms'
    
    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    """Product to track across platforms"""
    
    name = models.CharField(max_length=200, help_text="Product name (e.g., iPhone 15 Pro)", blank=True, null=True)
    category = models.CharField(max_length=100, help_text="Product category (e.g., Electronics, Accessories)", blank=True, null=True)
    description = models.TextField(help_text="Product description", blank=True, null=True)

    slug = models.SlugField(verbose_name="Slug", max_length=200, unique=True, blank=True, null=True, help_text="Auto Generated")
    image_url = ImageField(verbose_name="Product Image", upload_to=_generate_product_image, blank=True, null=True, help_text="Suggestion Size: 600px * 600px")
    is_active = models.BooleanField(default=True, help_text="Whether to track this product")
    
    class Meta:
        ordering = ['-created']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
    
    def __str__(self):
        return self.name
    
    def get_latest_prices(self):
        """Get the most recent price from each platform"""
        from django.db.models import Max
        
        latest_dates = self.prices.values('platform').annotate(
            latest_date=Max('scraped_at')
        )
        
        latest_prices = []
        for item in latest_dates:
            price = self.prices.filter(
                platform_id=item['platform'],
                scraped_at=item['latest_date']
            ).first()
            if price:
                latest_prices.append(price)
        
        return latest_prices
    
    def get_lowest_price(self):
        """Get the current lowest price across all platforms (converted to MYR)"""
        from .currency_utils import convert_to_myr
        
        latest_prices = self.get_latest_prices()
        if latest_prices:
            # Convert all to MYR for comparison
            return min(latest_prices, key=lambda x: convert_to_myr(x.price, x.currency))
        return None
    
    def get_highest_price(self):
        """Get the current highest price across all platforms (converted to MYR)"""
        from .currency_utils import convert_to_myr
        
        latest_prices = self.get_latest_prices()
        if latest_prices:
            # Convert all to MYR for comparison
            return max(latest_prices, key=lambda x: convert_to_myr(x.price, x.currency))
        return None
    
    def get_average_price(self):
        """Get the current average price across all platforms (in MYR)"""
        from .currency_utils import convert_to_myr
        
        latest_prices = self.get_latest_prices()
        if latest_prices:
            # Convert all to MYR first
            myr_prices = [convert_to_myr(p.price, p.currency) for p in latest_prices]
            total = sum(myr_prices)
            return total / len(myr_prices)
        return None

    def save(self, *args, **kwargs):
        model = self.__class__
        if not self.slug and self.name:
            slug = '{0}'.format(self.name)
            t_slug = slugify(unidecode(slug))

            origin = 1
            unique_slug = t_slug

            while model.objects.filter(slug=unique_slug).exists():
                unique_slug = '{}-{}'.format(t_slug, origin)
                origin += 1

            self.slug = unique_slug

        return super(Product, self).save(*args, **kwargs)

class ProductPrice(TimeStampedModel):
    """Historical price data for a product on a specific platform"""
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='prices',
        help_text="Product being tracked"
    )
    platform = models.ForeignKey(
        Platform,
        on_delete=models.CASCADE,
        related_name='prices',
        help_text="E-commerce platform"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Product price"
    )
    currency = models.CharField(
        max_length=10,
        default='MYR',
        help_text="Currency code (MYR, USD, etc.)"
    )
    product_url = models.URLField(
        max_length=2000,  # Increased to support long URLs (TaoBao, etc.)
        help_text="Direct link to product page",
        blank=True,
        null=True
    )
    scraped_at = models.DateTimeField(auto_now_add=True, help_text="When this price was scraped")
    
    # Optional fields
    availability = models.CharField(
        max_length=50,
        blank=True,
        default='Unknown',  # Default value for better data consistency
        help_text="Stock status (In Stock, Out of Stock, Limited Stock, Pre-Order, Unknown)"
    )
    seller_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Seller/shop name"
    )
    
    class Meta:
        ordering = ['-scraped_at']
        verbose_name = 'Product Price'
        verbose_name_plural = 'Product Prices'
        indexes = [
            models.Index(fields=['product', 'platform', '-scraped_at']),
        ]
    
    def get_price_in_myr(self):
        """Convert price to MYR"""
        from .currency_utils import convert_to_myr
        return convert_to_myr(self.price, self.currency)
    
    def get_price_display(self):
        """Get formatted price in RM (for templates)"""
        from .currency_utils import format_currency_myr
        myr_price = self.get_price_in_myr()
        return format_currency_myr(myr_price)
    
    def get_price_display_with_original(self):
        """Get price showing RM with original currency in parentheses"""
        from .currency_utils import format_currency_myr, normalize_currency_code
        
        normalized_currency = normalize_currency_code(self.currency)
        myr_price = self.get_price_in_myr()
        rm_display = format_currency_myr(myr_price)
        
        # If already in MYR/RM, just show RM
        if normalized_currency == 'MYR':
            return rm_display
        
        # Show both: RM xxx (AUD xxx)
        original_formatted = "{:,.2f}".format(self.price)
        return f"{rm_display} ({self.currency} {original_formatted})"
    
    def is_stale(self, hours=24):
        """Check if price data is older than specified hours"""
        if not self.scraped_at:
            return True
        cutoff_time = timezone.now() - timedelta(hours=hours)
        return self.scraped_at < cutoff_time
    
    def clean(self):
        """Validate price data before saving"""
        super().clean()
        
        # Validate price is positive
        if self.price is not None and self.price <= 0:
            raise ValidationError({'price': 'Price must be greater than 0'})
        
        # Validate currency code length
        if self.currency and len(self.currency) > 10:
            raise ValidationError({'currency': 'Currency code too long'})
        
        # Validate availability text length
        if self.availability and len(self.availability) > 50:
            raise ValidationError({'availability': 'Availability text too long (max 50 characters)'})
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        # Run validation before saving
        try:
            self.full_clean()
        except ValidationError as e:
            # Log validation errors but don't prevent save (for backwards compatibility)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Validation errors for ProductPrice: {e}")
        
        super().save(*args, **kwargs)
    
    
    def __str__(self):
        return f"{self.product.name} - {self.platform.name}: {self.currency} {self.price}"
