from django.db import models
from simple_history.models import HistoricalRecords
from django.utils import timezone
from users.models import User
from django.db.models import UniqueConstraint


class Service(models.Model):
    SERVICE_CHOICES = [
        ('tutoring', 'Tutoring'),
        ('accommodation', 'Accommodation'),
        ('jobs', 'Jobs'),
        ('internships', 'Internships'),
        ('ielts', 'IELTS Coaching'),
    ]

    name = models.CharField(max_length=32, choices=SERVICE_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def __str__(self):
        return f'{self.name}'


class SubscriptionTier(models.Model):
    TIER_LEVELS = [
        (1, "Platz Basic"),
        (2, "Platz Plus"),
        (3, "Platz Pro"),
        (4, "Platz Advanced"),
        (5, "Platz Elite"),
    ]

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('provider', 'Provider'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='tiers')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES,blank=True, null=True)
    stripe_price_id = models.CharField(max_length=100, help_text="Stripe Price ID for this tier")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    tier_level = models.IntegerField(choices=TIER_LEVELS)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
      
        constraints = [
        UniqueConstraint(fields=['service', 'role', 'tier_level'], name='unique_service_role_tier')
        ]
        ordering = ['tier_level']
    

    def __str__(self):
        return f" ({self.service.name}) -> {self.tier_level}"


class Subscription(models.Model):
    BILLING_INTERVAL_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('provider', 'Provider'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('trialing', 'Trialing'),
        ('past_due', 'Past Due'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscriptions")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscriptions")
    tier = models.ForeignKey(SubscriptionTier, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    cancellation_reason = models.TextField(blank=True, null=True)

    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_checkout_session_id = models.CharField(max_length=200, blank=True, null=True)

    amount = models.DecimalField(max_digits=7, decimal_places=2, help_text="Billed amount in EUR")
    billing_interval = models.CharField(max_length=10, choices=BILLING_INTERVAL_CHOICES, default='monthly')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('role', 'service', 'tier')
        ordering = ['tier__tier_level']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['service']),
            models.Index(fields=['tier']),
        ]

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

    def has_service(self):
        return self.service.name if self.service else None
    
    def __str__(self):
        return f"{self.user.email}"
    
