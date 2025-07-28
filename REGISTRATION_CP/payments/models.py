from django.db import models
from users.models import Tutor , User
from subscriptions.models import Subscription
from simple_history.models import HistoricalRecords


#============================================== User Premium Subscription Model ========================================================

class UserPremiumSubscriptionPayment(models.Model):

    user = models.ForeignKey(User, on_delete=models.SET_NULL,null=True,blank=True, related_name='user_premium_subscription_payments')
    subscription = models.ForeignKey(Subscription,on_delete=models.SET_NULL,null=True,blank=True,related_name="user_premium_subscription_payments")

    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    price_id = models.CharField(max_length=100, help_text="Stripe Price ID used for the subscription")

    amount_paid = models.DecimalField(max_digits=8, decimal_places=2)
    amount_received_at_stripe = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stripe_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    net_received_from_stripe = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    payment_status = models.CharField(
        max_length=50,
        choices=[
            ('paid', 'Paid'),
            ('unpaid', 'Unpaid'),
            ('refunded', 'Refunded'),
            ('failed', 'Failed'),
            ('canceled', 'Canceled'),
        ],
        default='unpaid'
    )

    billing_reason = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)

    cancel_at = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(blank=True, null=True)
    
    metadata = models.JSONField(blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f" PUS - ({self.user.email}) - {self.payment_status}"


#============================================== Tutor Premium Subscription Model ========================================================


class TutorPremiumSubscriptionPayment(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL,null=True,blank=True, related_name='tutor_premium_subscription_payments')
    tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL,null=True,blank=True, related_name='premium_subscription_payments')
    subscription = models.ForeignKey(Subscription,on_delete=models.SET_NULL,null=True,blank=True,related_name="tutor_premium_subscription_payments")

    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    price_id = models.CharField(max_length=100, help_text="Stripe Price ID used for the subscription")

    amount_paid = models.DecimalField(max_digits=8, decimal_places=2)
    amount_received_at_stripe = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stripe_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    net_received_from_stripe = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    payment_status = models.CharField(
        max_length=50,
        choices=[
            ('paid', 'Paid'),
            ('unpaid', 'Unpaid'),
            ('refunded', 'Refunded'),
            ('failed', 'Failed'),
            ('canceled', 'Canceled'),
        ],
        default='unpaid'
    )

    billing_reason = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)

    cancel_at = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(blank=True, null=True)

    metadata = models.JSONField(blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f" PTS - ({self.tutor.user.email}) - {self.payment_status}"
