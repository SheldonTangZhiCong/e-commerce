from django.contrib import admin
from core.admin import MixinModelAdmin
from .models import Platform, Product, ProductPrice


@admin.register(Platform)
class PlatformAdmin(MixinModelAdmin):
    list_display = ['name', 'base_url', 'currency', 'is_active']
    list_filter = ['is_active', 'currency']
    search_fields = ['name', 'base_url']


class ProductPriceInline(admin.TabularInline):
    """Inline for adding product URLs when creating/editing products"""
    model = ProductPrice
    extra = 1
    fields = ['platform', 'product_url', 'price', 'currency', 'availability']
    verbose_name = '平台价格信息'
    verbose_name_plural = '平台价格信息（首次添加时请填写 product_url）'


@admin.register(Product)
class ProductAdmin(MixinModelAdmin):
    list_display = ['name', 'category', 'is_active']
    list_filter = ['is_active', 'category']
    search_fields = ['name', 'description']
    inlines = [ProductPriceInline]
    
    def get_inline_instances(self, request, obj=None):
        """Show inline only when editing existing product"""
        if obj:  # Only show when editing existing product
            return super().get_inline_instances(request, obj)
        return []


@admin.register(ProductPrice)
class ProductPriceAdmin(MixinModelAdmin):
    list_display = ['product', 'platform', 'price', 'currency', 'scraped_at', 'availability']
    list_filter = ['platform', 'currency', 'scraped_at', 'availability']
    search_fields = ['product__name', 'platform__name', 'seller_name']
    date_hierarchy = 'scraped_at'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product', 'platform')