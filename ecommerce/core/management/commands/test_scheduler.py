"""
Management command to manually run the scheduler job for testing
"""
from django.core.management.base import BaseCommand
from apps.products.scheduler import scrape_all_products_job


class Command(BaseCommand):
    help = 'Manually run the scheduled scraper job (for testing)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Running scheduler job manually...'))
        
        try:
            scrape_all_products_job()
            self.stdout.write(self.style.SUCCESS('✓ Scheduler job completed successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
