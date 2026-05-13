from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from monitoring.models import Screenshot
import os

class Command(BaseCommand):
    help = 'Delete screenshots older than 24 hours'

    def handle(self, *args, **options):
        threshold = timezone.now() - timedelta(hours=24)
        old_screenshots = Screenshot.objects.filter(captured_at__lt=threshold)
        count = old_screenshots.count()
        
        for ss in old_screenshots:
            # Delete the actual file from storage
            if ss.image:
                if os.path.isfile(ss.image.path):
                    os.remove(ss.image.path)
            ss.delete()
            
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} old screenshots.'))
