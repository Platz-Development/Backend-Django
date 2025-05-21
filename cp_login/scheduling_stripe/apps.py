from django.apps import AppConfig


class SchedulingStripeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduling_stripe'
    
    def ready(self):
        import scheduling_stripe.signals