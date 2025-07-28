from django.urls import path
from .views import StripeSubscriptionWebhookView

urlpatterns = [
    path("stripe/subscription-webhook/", StripeSubscriptionWebhookView.as_view(), name="stripe-subscription-webhook"),
]
