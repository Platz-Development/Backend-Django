import os
from django.apps import AppConfig
from django.conf import settings

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        os.makedirs(os.path.join(settings.BASE_DIR, 'logs', 'users'), exist_ok=True)
