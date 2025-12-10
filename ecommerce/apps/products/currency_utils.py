"""
Currency conversion utilities for price normalization
"""
from decimal import Decimal
from django.core.cache import cache
import requests
import logging

logger = logging.getLogger(__name__)

# Fixed exchange rates (update periodically or use API)
EXCHANGE_RATES = {
    'MYR': Decimal('1.0'),     # Base currency
    'RM': Decimal('1.0'),      # Same as MYR
    'AUD': Decimal('3.18'),    # 1 AUD ≈ 3.18 MYR (as of Dec 2024)
    'USD': Decimal('4.67'),    # 1 USD ≈ 4.67 MYR
    'SGD': Decimal('3.48'),    # 1 SGD ≈ 3.48 MYR
    'CNY': Decimal('0.65'),    # 1 CNY ≈ 0.65 MYR
    'EUR': Decimal('5.10'),    # 1 EUR ≈ 5.10 MYR
    'GBP': Decimal('5.95'),    # 1 GBP ≈ 5.95 MYR
}


def normalize_currency_code(currency):
    """
    Normalize currency codes to standard format
    
    Args:
        currency: Currency code (MYR, RM, AUD, etc.)
        
    Returns:
        Normalized currency code
    """
    if not currency:
        return 'MYR'
    
    currency = str(currency).upper().strip()
    
    # Normalize RM to MYR
    if currency == 'RM':
        return 'MYR'
    
    return currency


def convert_to_myr(amount, from_currency):
    """
    Convert amount from any currency to MYR
    
    Args:
        amount: Price amount (Decimal or float)
        from_currency: Source currency code
        
    Returns:
        Decimal amount in MYR
    """
    if not amount:
        return Decimal('0.0')
    
    amount = Decimal(str(amount))
    from_currency = normalize_currency_code(from_currency)
    
    # Already in MYR
    if from_currency == 'MYR':
        return amount
    
    # Get exchange rate
    rate = EXCHANGE_RATES.get(from_currency)
    
    if not rate:
        logger.warning(f"Unknown currency: {from_currency}, using 1:1 rate")
        return amount
    
    # Convert to MYR
    myr_amount = amount * rate
    
    logger.info(f"Converted {amount} {from_currency} to {myr_amount} MYR (rate: {rate})")
    
    return myr_amount


def format_currency_myr(amount):
    """
    Format amount as RM currency string
    
    Args:
        amount: Decimal amount
        
    Returns:
        Formatted string like "RM 5,379.00"
    """
    if not amount:
        return "RM 0.00"
    
    amount = Decimal(str(amount))
    
    # Format with thousand separators
    formatted = "{:,.2f}".format(amount)
    
    return f"RM {formatted}"


def get_live_exchange_rate(from_currency, to_currency='MYR', api_key=None):
    """
    Get live exchange rate from API (optional premium feature)
    
    Args:
        from_currency: Source currency
        to_currency: Target currency (default MYR)
        api_key: Optional API key for exchange rate service
        
    Returns:
        Decimal exchange rate or None if failed
    """
    # This is a placeholder for live API integration
    # You can use services like:
    # - exchangerate-api.com
    # - currencyapi.com
    # - fixer.io
    
    cache_key = f'exchange_rate_{from_currency}_{to_currency}'
    cached_rate = cache.get(cache_key)
    
    if cached_rate:
        return Decimal(str(cached_rate))
    
    # For now, use fixed rates
    return EXCHANGE_RATES.get(normalize_currency_code(from_currency))


# Quick access functions
def to_rm(amount, currency):
    """Shorthand for convert_to_myr and format"""
    myr_amount = convert_to_myr(amount, currency)
    return format_currency_myr(myr_amount)
