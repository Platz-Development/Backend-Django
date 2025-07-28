from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ExportMixin
from import_export import resources

from .models import UserPremiumSubscriptionPayment, TutorPremiumSubscriptionPayment

# =========================== RESOURCES ============================

class UserPremiumSubscriptionResource(resources.ModelResource):
    class Meta:
        model = UserPremiumSubscriptionPayment

class TutorPremiumSubscriptionResource(resources.ModelResource):
    class Meta:
        model = TutorPremiumSubscriptionPayment


# =========================== ADMINS ===============================

@admin.register(UserPremiumSubscriptionPayment)
class UserPremiumSubscriptionAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = UserPremiumSubscriptionResource
    autocomplete_fields = ['user']
    list_display = (
        'user', 'stripe_subscription_id', 'amount_paid',
        'payment_status', 'is_active', 'start_date', 'end_date', 'created_at'
    )
    list_filter = ('payment_status', 'is_active', 'cancel_at_period_end')
    search_fields = ('user__email', 'stripe_subscription_id', 'stripe_customer_id', 'stripe_invoice_id')
    readonly_fields = ('created_at', 'updated_at', 'stripe_subscription_id', 'stripe_customer_id', 'stripe_invoice_id','amount_paid',)

    fieldsets = (
        ('Main Info', {
            'fields': ('user','is_active')
        }),
        ('Stripe Info', {
            'fields': (
                'stripe_subscription_id', 'stripe_payment_intent_id',
                'stripe_customer_id', 'stripe_invoice_id', 'price_id'
            )
        }),
        ('Payment Details', {
            'fields': ('amount_paid', 'payment_status', 'billing_reason', )
        }),
        ('Subscription Duration', {
            'fields': ('start_date', 'end_date', 'cancel_at', 'cancel_at_period_end', 'canceled_at')
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('metadata',)
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(TutorPremiumSubscriptionPayment)
class TutorPremiumSubscriptionAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = TutorPremiumSubscriptionResource
    autocomplete_fields = ['tutor']
    list_display = (
        'tutor', 'stripe_subscription_id', 'amount_paid',
        'payment_status', 'is_active', 'start_date', 'end_date', 'created_at'
    )
    list_filter = ('payment_status', 'is_active', 'cancel_at_period_end')
    search_fields = ('tutor__user__email', 'stripe_subscription_id', 'stripe_customer_id', 'stripe_invoice_id')
    readonly_fields = ('created_at', 'updated_at', 'stripe_subscription_id', 'stripe_customer_id', 'stripe_invoice_id','amount_paid',)

    fieldsets = (
        ('Main Info', {
            'fields': ('tutor','is_active')
        }),
        ('Stripe Info', {
            'fields': (
                'stripe_subscription_id', 'stripe_payment_intent_id',
                'stripe_customer_id', 'stripe_invoice_id', 'price_id'
            )
        }),
        ('Payment Details', {
            'fields': ('amount_paid', 'payment_status', 'billing_reason', )
        }),
        ('Subscription Duration', {
            'fields': ('start_date', 'end_date', 'cancel_at', 'cancel_at_period_end', 'canceled_at')
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('metadata',)
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
