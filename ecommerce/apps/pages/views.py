"""
All views for the e-commerce price comparison system
"""
from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import timedelta
from apps.products.models import Product, ProductPrice, Platform
import json
import logging

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    """Class-based view for home page"""
    template_name = 'pages/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get 6 most recent products with price information
        products = Product.objects.filter(is_active=True).prefetch_related('prices__platform')[:6]
        
        # Add price summary for each product
        for product in products:
            latest_prices = product.get_latest_prices()
            product.lowest_price_obj = product.get_lowest_price()
            product.highest_price_obj = product.get_highest_price()
            product.average_price = product.get_average_price()
            product.platform_count = len(latest_prices)
        
        context['products'] = products
        return context


class ProductListView(ListView):
    """Class-based view for product list page"""
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        """Get all active products with price information"""
        return Product.objects.filter(is_active=True).prefetch_related('prices__platform')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = context['products']
        
        # Add price summary for each product
        for product in products:
            latest_prices = product.get_latest_prices()
            product.lowest_price_obj = product.get_lowest_price()
            product.highest_price_obj = product.get_highest_price()
            product.average_price = product.get_average_price()
            product.platform_count = len(latest_prices)
        
        return context


class ProductDetailView(DetailView):
    """Class-based view for product detail page"""
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        """Only show active products"""
        return Product.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = context['product']
        
        # Get latest prices from each platform
        latest_prices = product.get_latest_prices()
        
        # Get price statistics
        lowest_price = product.get_lowest_price()
        highest_price = product.get_highest_price()
        average_price = product.get_average_price()
        
        # Get 7-day price history for charts
        seven_days_ago = timezone.now() - timedelta(days=7)
        price_history = ProductPrice.objects.filter(
            product=product,
            scraped_at__gte=seven_days_ago
        ).select_related('platform').order_by('scraped_at')
        
        # Organize price history by platform for chart
        chart_data = {}
        platforms = Platform.objects.filter(is_active=True)
        
        for platform in platforms:
            platform_prices = price_history.filter(platform=platform)
            if platform_prices.exists():
                chart_data[platform.name] = {
                    'dates': [p.scraped_at.strftime('%Y-%m-%d %H:%M') for p in platform_prices],
                    'prices': [float(p.price) for p in platform_prices],
                }
        
        # Convert chart_data to JSON for template
        chart_data_json = mark_safe(json.dumps(chart_data, ensure_ascii=False))
        
        # Generate AI summary
        ai_summary = generate_price_summary(product, latest_prices, lowest_price, average_price)
        
        context.update({
            'latest_prices': latest_prices,
            'lowest_price': lowest_price,
            'highest_price': highest_price,
            'average_price': average_price,
            'chart_data': chart_data,
            'chart_data_json': chart_data_json,
            'ai_summary': ai_summary,
        })
        
        return context


def generate_price_summary(product, latest_prices, lowest_price, average_price):
    """
    Generate AI summary for price comparison
    
    Args:
        product: Product instance
        latest_prices: List of latest ProductPrice instances
        lowest_price: ProductPrice instance with lowest price
        average_price: Average price value
        
    Returns:
        String summary
    """
    if not latest_prices or not lowest_price:
        return "No price data available."
    
    currency = lowest_price.currency or 'MYR'
    platform_name = lowest_price.platform.name
    
    # Calculate price difference
    if len(latest_prices) > 1 and average_price:
        price_diff = float(average_price) - float(lowest_price.price)
        price_diff_percent = (price_diff / float(average_price)) * 100 if average_price > 0 else 0
        
        if price_diff_percent > 10:
            savings = f"You can save approximately {price_diff_percent:.1f}%"
        else:
            savings = "Price difference is minimal"
    else:
        savings = ""
    
    # Format price
    if currency == 'MYR':
        price_str = f"RM{lowest_price.price:.2f}"
    elif currency == 'USD':
        price_str = f"${lowest_price.price:.2f}"
    else:
        price_str = f"{lowest_price.price:.2f} {currency}"
    
    summary = f"Current lowest price is {price_str}, recommended to buy from {platform_name}."
    
    if savings:
        summary += f" {savings}."
    
    return summary