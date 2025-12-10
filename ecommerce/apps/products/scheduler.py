"""
Scheduler configuration for automatic price scraping
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django_apscheduler.models import DjangoJobExecution
import logging

logger = logging.getLogger(__name__)


def scrape_all_products_job():
    """Job function to scrape all products"""
    from .scraper_service import ScraperService
    
    logger.info("Starting scheduled price scraping...")
    try:
        results = ScraperService.scrape_all_products()
        logger.info(
            f"Scheduled scraping completed: "
            f"{results['scraped_products']}/{results['total_products']} products, "
            f"{results['total_prices']} prices collected"
        )
    except Exception as e:
        logger.error(f"Error in scheduled scraping: {e}")


def start_scheduler():
    """Start the APScheduler"""
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Schedule daily scraping at 8 AM
    scheduler.add_job(
        scrape_all_products_job,
        trigger=CronTrigger(hour=8, minute=00),  # Run daily at 8 AM
        id="daily_price_scraping",
        name="Daily Price Scraping",
        replace_existing=True,
    )

    register_events(scheduler)
    
    try:
        logger.info("Starting scheduler...")
        scheduler.start()
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")

