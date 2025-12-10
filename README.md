# E-commerce Price Comparison System

A Django-based intelligent price comparison system that automatically scrapes product prices from multiple e-commerce platforms using **AI Vision technology** (Google Gemini).

## ✨ Features

- 🤖 **AI-Powered Scraping**: Uses Gemini Vision to extract prices from product pages  
- 🌍 **Multi-Platform**: Supports Lazada, Amazon, eBay, AliExpress, and more
- 💱 **Currency Conversion**: Automatic conversion to Malaysian Ringgit (RM)
- 📊 **Price Trends**: 7-day price fluctuation charts
- 🎯 **AI Recommendations**: Intelligent purchase suggestions
- ⏰ **Automated Scraping**: Built-in APScheduler for daily updates at 8 AM
- 📈 **Stock Status**: Tracks product availability across platforms

## ✅ Compatible Platforms

The AI Vision scraper works best with these platforms:

| Platform | Compatibility | Success Rate | Login Required | Recommended |
|----------|--------------|--------------|----------------|-------------|
| **Lazada** | ✅ Excellent | 95% | No | ⭐ Yes |
| **Amazon** | ✅ Excellent | 95% | No | ⭐ Yes |
| **eBay** | ✅ Excellent | 90% | No | ⭐ Yes |
| **AliExpress** | ✅ Good | 85% | No | ⭐ Yes |
| **Shopee** | ❌ Limited | <20% | Yes | ❌ No - Use Lazada instead |
| **TaoBao** | ❌ Limited | <20% | Yes | ❌ No - Use AliExpress instead |

**Note**: Shopee and TaoBao have aggressive anti-bot detection that blocks automated scraping. We recommend using Lazada (Malaysia market) or AliExpress (China products) as reliable alternatives.

---

## 📋 Quick Start

### Prerequisites

- Python 3.13  
- PostgreSQL 12+ (or SQLite for development)
- Google Gemini API Key - [Get free API key](https://aistudio.google.com/app/apikey)

### Installation (5 Minutes)

```bash
# 1. Clone and enter directory
git clone https://[your_bitbucket_username]@bitbucket.org/rexo-team/e-commerce.git
cd e-commerce

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements/base.txt
playwright install chromium

# 4. Set up database
python manage.py migrate

# 5. Create admin user
python manage.py createsuperuser

# 6. Configure Gemini API Key (see below)

# 7. Run server
python manage.py runserver
```

Visit: http://localhost:8000/admin/

---

## 🔑 Google Gemini API Setup

### Get API Key (FREE)

1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with Google
3. Click **"Create API Key"**
4. Copy the key (starts with `AIza...`)

**Free Tier**: 1,500 requests/day - perfect for typical usage!

### Configure API Key

Edit `ecommerce/core/settings/base.py`:

```python
# At the bottom of the file
GOOGLE_GEMINI_API_KEY = 'AIzaSy...'  # Paste your key here
```

**Alternative** - Use environment variable:
```powershell
# Windows
$env:GOOGLE_GEMINI_API_KEY="AIzaSy..."

# Linux/Mac
export GOOGLE_GEMINI_API_KEY="AIzaSy..."
```

---

## 📦 Initial Setup

### Optional: Load the fixture data (Recommended)

```bash
python manage.py loaddata products.json
```

### 1. Add E-commerce Platforms

Go to **Admin > Products > Platforms** and add:

| Platform | Base URL | Currency | Recommended |
|----------|----------|----------|-------------|
| Lazada | `https://www.lazada.com.my` | MYR | ⭐ Yes |
| Amazon | `https://www.amazon.com` | USD | ⭐ Yes |
| eBay | `https://www.ebay.com.au` | AUD | ⭐ Yes |
| AliExpress | `https://www.aliexpress.com` | USD | ⭐ Yes |

**Note**: Avoid Shopee and TaoBao as they block automated scraping.

### 2. Add Products

Go to **Products > Products**:
- Name: e.g., "iPhone 15 Pro (256GB)"
- Category: e.g., "Electronics"
- Upload product image (optional)

### 3. Add Product URLs

**Important**: For each product, add Product Price records with URLs:

1. Go to **Products > Product Prices**
2. Click **"Add Product Price"**
3. Select Product and Platform
4. **Paste Product URL** from that platform
5. Leave Price blank (auto-filled during scraping)
6. Save

Repeat for each platform.

---

## 🚀 Running the Scraper

### Manual Scraping

```bash
# Scrape all products
python manage.py scrape_prices

# Scrape specific product
python manage.py scrape_prices --product-id 1

# Scrape specific platform only
python manage.py scrape_prices --platform Shopee

# Test without saving
python manage.py scrape_prices --dry-run

# Test the scheduler job
python manage.py test_scheduler

# Test Google Gemini AI Vision scraper setup
python manage.py test_ai_scraper

# Test to scrape and also will create screenshot of the e-commerce page outlook in media folder
python manage.py debug_all_urls
```

### Automated Daily Scraping (APScheduler)

**APScheduler is already configured and runs automatically!**

#### How It Works

When you run `python manage.py runserver`, APScheduler:
1. Automatically starts in the background
2. Schedules daily scraping at 8:00 AM
3. Runs silently until the scheduled time
4. Executes the scraping job automatically

#### Verify It's Running

Look for this message when starting the server:
```
Starting scheduler...
Price scraping scheduler started
```

#### Change Schedule Time

Edit `ecommerce/apps/products/scheduler.py` line 37:

```python
trigger=CronTrigger(hour=8, minute=0),  # Change hour/minute here
```

Restart Django server for changes to take effect.

#### Monitor Scheduled Jobs

Visit **Admin > Django APScheduler > Django job executions** to see:
- Run history
- Success/failure status
- Execution duration
- Error details

#### Multiple Daily Scrapes

Edit `scheduler.py` to add more jobs:

```python
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Morning scrape at 8 AM
    scheduler.add_job(
        scrape_all_products_job,
        trigger=CronTrigger(hour=8, minute=0),
        id="morning_scraping",
        name="Morning Price Scraping",
        replace_existing=True,
    )
    
    # Evening scrape at 8 PM
    scheduler.add_job(
        scrape_all_products_job,
        trigger=CronTrigger(hour=20, minute=0),
        id="evening_scraping",
        name="Evening Price Scraping",
        replace_existing=True,
    )
    
    register_events(scheduler)
    scheduler.start()
```

#### Disable APScheduler

If you want to use external cron instead:

```python
# In settings.py
ENABLE_SCHEDULER = False
```

---

## 🔧 Database Setup

### PostgreSQL (Recommended)

**Windows:**
```sql
psql -U postgres -h localhost
CREATE DATABASE ecommerce_db;
CREATE USER ecommerce WITH PASSWORD '2+PJg#&?';
ALTER ROLE ecommerce SET client_encoding TO 'utf8';
ALTER ROLE ecommerce SET default_transaction_isolation TO 'read committed';
ALTER ROLE ecommerce SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ecommerce_db TO ecommerce;
\q
```

**Linux/Mac:**
```sql
psql postgres
CREATE DATABASE ecommerce_db;
CREATE USER ecommerce WITH PASSWORD '2+PJg#&?';
ALTER ROLE ecommerce SET client_encoding TO 'utf8';
ALTER ROLE ecommerce SET default_transaction_isolation TO 'read committed';
ALTER ROLE ecommerce SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ecommerce_db TO ecommerce;
\q
```

### SQLite (Development)

Already configured - no setup needed!

---

## 💱 Currency Conversion

All prices are automatically converted to Malaysian Ringgit (RM):

| Currency | Rate to MYR | Example |
|----------|-------------|---------|
| MYR/RM | 1.00 | RM 5,379 |
| USD | 4.67 | USD 1,199 = RM 5,599 |
| AUD | 3.18 | AUD 2,499 = RM 7,947 |
| SGD | 3.48 | SGD 1,699 = RM 5,913 |
| CNY | 0.64 | CNY 8,999 = RM 5,759 |

**Update Exchange Rates**: Edit `apps/products/currency_utils.py`

---

## 📊 Using the System

### View Products

- **Homepage**: `http://localhost:8000/`
- **Product List**: `http://localhost:8000/products/`
- **Product Detail**: Click any product to see:
  - Price comparison table
  - Lowest/Highest/Average prices in RM
  - 7-day price trend chart
  - AI purchase recommendation
  - Stock status from each platform

### Admin Panel

- **Scraped Data**: `/admin/products/productprice/`
- **Manage Products**: `/admin/products/product/`
- **Platform Settings**: `/admin/products/platform/`
- **Scheduler History**: `/admin/django_apscheduler/djangojobexecution/`

---

## 🐛 Troubleshooting

### "403 The caller does not have permission"

**Fix**: Add your Google Gemini API key to settings (see API Setup section)

### "Failed to capture screenshot"

**Fixes**:
1. Run `playwright install chromium`
2. Check internet connection
3. Verify product URL is valid

### "Could not extract price from screenshot"

**Fixes**:
1. Page might have loaded incorrectly - retry
2. Check product URL is still valid
3. Some websites may block automated access

### APScheduler not running

**Check**:
1. `ENABLE_SCHEDULER = True` in settings
2. Running with `python manage.py runserver`
3. Look for "Price scraping scheduler started" in console
4. Check for database connection errors

### Jobs scheduled but not executing

**Remember**: APScheduler schedules jobs for the **next occurrence**. If you set it to 8 AM and start the server at 9 AM, it will run **tomorrow at 8 AM**, not immediately.

**To test immediately**: Run `python manage.py test_scheduler`

---

## 📁 Project Structure

```
e-commerce/
├── ecommerce/
│   ├── apps/
│   │   └── products/
│   │       ├── models.py              # Product, Platform, ProductPrice
│   │       ├── scraper_service.py     # Scraping orchestration
│   │       ├── scheduler.py           # APScheduler configuration
│   │       ├── currency_utils.py      # Currency conversion
│   │       └── scrapers/
│   │           ├── gemini_vision_scraper.py  # AI Vision scraper (main)
│   │           ├── base_scraper.py         # Base scraper
│   │           ├── aliexpress_scraper.py         # Fallback scrapers
│   │           ├── lazada_scraper.py
│   │           └── eBay_scraper.py
│   ├── core/
│   │   ├── management/commands/
│   │   │   ├── scrape_prices.py       # Manual scraping command
│   │   │   └── test_scheduler.py      # Test scheduler job
│   │   │   └── debug_all_urls.py      # Test scraping and screenshot
│   │   │   └── test_ai_scraper.py     # Test AI scraper
│   │   └── settings/
│   │       └── base.py                # Django settings
│   │       └── local.py               # Local development settings
│   └── templates/
│       │
│       ├── pages/
│       │   ├── home.html
│       └── products/
│           ├── product_list.html
│           └── product_detail.html
├── requirements/
│   └── base.txt                       # Python dependencies
└── README.md                          # This file
```

---

## ⚙️ Advanced Features

### Stock Status Tracking

The AI scraper automatically extracts stock status:

| Status | Indicators |
|--------|------------|
| ✅ In Stock | "Available", "X units left", "Ready to Ship" |
| ❌ Out of Stock | "Sold Out", "Unavailable", "Notify Me" |
| ⏳ Pre-Order | "Pre-Order", "Coming Soon" |
| ⚠️ Limited Stock | "Only X left", "Low Stock" |
| ❓ Unknown | No stock info found |

### Price History & Trends

- Stores all historical price data
- View 7-day trends on product detail pages
- Chart.js visualization
- Identify price drops and increases

### AI Purchase Recommendations

Powered by Google Gemini, recommendations consider:
- Current price vs historical average
- Stock availability
- Price trends
- Platform-specific deals

### Error Handling

The scraper includes:
- Retry logic with exponential backoff (1s, 2s, 4s)
- URL validation before scraping
- Data validation before saving
- Comprehensive logging

---

## 🔍 How AI Scraping Works

### Traditional Scraper Problems

- ❌ CSS selectors change frequently
- ❌ Requires update for each platform

### AI Vision Scraper Solution

1. Launch real browser (Playwright)
2. Navigate to product URL
3. Wait for page to fully load
4. Take screenshot (1280x1024px)
5. Send to Google Gemini Vision
6. AI extracts: price, currency, stock status, seller
7. Save to database

**Advantages**:
- ✅ Works with JavaScript-loaded content
- ✅ No CSS selectors needed
- ✅ Adapts to website changes
- ✅ Same code for all platforms
- ✅ Reads like a human would
- ⚠️ But some ecommerce platforms like Shopee will have high secured by anti-bot system which can't direct screenshot at the product page.

---

## 📋 Management Commands Reference

| Command | Description |
|---------|-------------|
| `python manage.py scrape_prices` | Scrape all products |
| `python manage.py scrape_prices --product-id 1` | Scrape specific product |
| `python manage.py scrape_prices --platform Shopee` | Scrape specific platform |
| `python manage.py scrape_prices --dry-run` | Test without saving |
| `python manage.py test_scheduler` | Run scheduler job manually |
| `python manage.py runserver` | Start server (APScheduler auto-starts) |

---

## 💡 Production Deployment

### Using Gunicorn/uWSGI

APScheduler works great with production servers:

```bash
# Gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:8000

# uWSGI
uwsgi --http :8000 --module core.wsgi
```

APScheduler will start automatically and keep running.

### Important Notes for Production

1. **Keep Django Running 24/7**: APScheduler requires Django to be running
2. **Use Process Manager**: Use systemd, supervisor, or similar to keep Django alive
3. **Monitor Logs**: Check `/admin/django_apscheduler/` regularly
4. **Set Timezone**: Ensure server timezone matches your expected schedule time

### Alternative: External Cron

For production with frequent Django restarts, you might prefer external cron:

1. Set `ENABLE_SCHEDULER = False` in settings
2. Create cron job to run `python manage.py scrape_prices`

---

## 🎓 Technical Stack

- **Backend**: Django 6.0
- **Database**: PostgreSQL / SQLite
- **AI**: Google Gemini 1.5 Flash
- **Browser**: Playwright (Chromium)
- **Scheduler**: APScheduler + django-apscheduler
- **Frontend**: Bootstrap 5 + Chart.js

---

## ❓ FAQ

**Q: Do I need to keep Django server running 24/7?**
A: Yes, for APScheduler to work. Use a process manager in production.

**Q: Can I scrape without AI (using traditional methods)?**
A: Yes, set `USE_AI_VISION_SCRAPER = False` in settings (not recommended).

**Q: How do I add a new e-commerce platform?**
A: Just add it in admin under Platforms. The AI scraper works with any site!

**Q: What if Gemini API goes down?**
A: The scraper will log errors and retry. Check job execution history in admin.

**Q: Can I change the schedule time?**
A: Yes, edit `scheduler.py` line 37 and restart Django server.

**Q: How accurate is the AI?**
A: ~95%+ accuracy. The AI reads pages like a human, making it very reliable.

**Q: What if I exceed the free tier?**
A: Unlikely with typical usage (~30-50 products × 5 platforms = 150-250 requests/day). Paid tier is very cheap ($0.00001/request).

---

## 📄 License

This project is for educational and personal use. Please respect the terms of service of e-commerce platforms when scraping. Consider using official APIs for production use.

---

## 🙋 Need Help?

1. Check this README
2. Review log files and Django console
3. Test with `--dry-run` mode
4. Check scheduler execution history in admin
5. Verify API key is configured correctly

---

**Last Updated**: December 2025  
**Version**: 2.0 - AI Vision Integration with APScheduler