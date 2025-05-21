from django.urls import path
from .views import LiveClassPaymentIntent, stripe_webhook,CoursePurchasePaymentIntent
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('payments/create-live-class-payment-intent/', LiveClassPaymentIntent.as_view(), name='create-live-class-payment-intent'),
    path('stripe-webhook/', csrf_exempt(stripe_webhook), name='stripe_webhook'),
    path('payments/create-course-purchase-payment-intent/', CoursePurchasePaymentIntent.as_view(), name='create-course-purchase-payment-intent'),
    



]