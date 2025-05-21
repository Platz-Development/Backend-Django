import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cp_login.settings")
django.setup()

from django.contrib.sites.models import Site

def fix_site():
    try:
        site = Site.objects.get(id=1)
        site.domain = '127.0.0.1:8000'
        site.name = 'localhost'
        site.save()
        print("✅ Existing Site updated.")
    except Site.DoesNotExist:
        Site.objects.create(id=1, domain='127.0.0.1:8000', name='localhost')
        print("✅ New Site created.")

if __name__ == "__main__":
    fix_site()
