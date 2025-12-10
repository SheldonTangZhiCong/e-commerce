from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class ProductsConfig(AppConfig):
    name = 'apps.products'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """Start scheduler when app is ready"""
        import sys
        from django.conf import settings
        
        # Only start scheduler if running the server (not migrations, tests, etc.)
        if len(sys.argv) > 1 and sys.argv[1] in ['runserver', 'runserver_plus']:
            # Delay scheduler startup to avoid database access during app initialization
            if getattr(settings, 'ENABLE_SCHEDULER', True):
                try:
                    # Import and start scheduler in a delayed manner using threading
                    import threading
                    from django.db import connections
                    
                    def delayed_start():
                        """Start scheduler after a delay to avoid DB access during initialization"""
                        import time
                        time.sleep(3)  # Wait 3 seconds for DB to be ready
                        try:
                            # Close any existing connections
                            connections.close_all()
                            from .scheduler import start_scheduler
                            start_scheduler()
                            logger.info("Price scraping scheduler started")
                        except Exception as e:
                            logger.error(f"Failed to start scheduler: {e}")
                    
                    # Start in a separate daemon thread
                    timer = threading.Timer(3.0, delayed_start)
                    timer.daemon = True
                    timer.start()
                except Exception as e:
                    logger.error(f"Failed to setup scheduler: {e}")
