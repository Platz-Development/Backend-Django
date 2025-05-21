import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cp_login.settings')
app = Celery('cp_login')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()