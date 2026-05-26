from django.core.management.base import BaseCommand
from ingestion.models import Client

class Command(BaseCommand):
    help = 'Seeds the production multi-tenancy corporate client row'

    def handle(self, *args, **options):
        # Create or fetch the mandatory corporate tenant anchor row
        client, created = Client.objects.get_or_create(
            slug="acme-manufacturing",
            defaults={"name": "Acme Manufacturing Pvt Ltd", "timezone": "Asia/Kolkata"}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('>>> Created corporate tenant row: acme-manufacturing'))
        else:
            self.stdout.write(self.style.SUCCESS('>>> Corporate tenant anchor verified.'))