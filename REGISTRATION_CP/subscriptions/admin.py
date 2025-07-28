from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ExportMixin
from import_export import resources

from .models import Service,Subscription,SubscriptionTier


class ServiceResource(resources.ModelResource):
    class Meta:
        model = Service
        fields = ('id', 'name', 'description', 'is_active', 'created_at', 'updated_at')
        export_order = fields

@admin.register(Service)
class ServiceAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = ServiceResource
    list_display = ('id','name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'name')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('name',)
    
    fieldsets = (
        ('Service Details', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )

class SubscriptionResource(resources.ModelResource):
    class Meta:
        model = Subscription
        fields = (
            'id', 'user__email', 'amount_eur', 'billing_interval', 
            'start_date', 'end_date', 'is_active',
            'stripe_subscription_id', 'stripe_customer_id',
            'stripe_price_id', 'stripe_checkout_session_id',
            'created_at', 'updated_at'
        )
        export_order = fields


@admin.register(Subscription)
class SubscriptionAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = SubscriptionResource
    autocomplete_fields = ['user', 'service',]
    list_select_related = ('user', 'service', 'tier')
    list_display = ('user','role','service','tier','status', 'amount', 'billing_interval', 'is_active', 'start_date', 'end_date',)
    list_filter = ('billing_interval','role', 'is_active', 'start_date', 'end_date', 'created_at','tier')
    search_fields = ('user__email', 'stripe_subscription_id', 'stripe_customer_id', 'stripe_price_id')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Main Info', {
            'fields': ('user','role', 'service','tier','status')
        }),
        ('Subscription Period', {
            'fields': ('start_date', 'end_date', 'is_active', 'billing_interval','cancellation_reason')
        }),
        ('Stripe Information', {
            'classes': ('collapse',),
            'fields': (
                'stripe_subscription_id', 'stripe_customer_id',
                'stripe_price_id', 'stripe_checkout_session_id'
            )
        }),
        ('Price Details', {
            'fields': ('amount',)
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )


class SubscriptionTierResource(resources.ModelResource):
    class Meta:
        model = SubscriptionTier
        fields = (
            'id', 'service__name', 'tier_level','role',
            'stripe_price_id', 'price', 'description',
            'created_at', 'updated_at',
        )
        export_order = fields


@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = SubscriptionTierResource
    autocomplete_fields = ['service']
    list_display = (
       'id', 'service', 'tier_level','role', 'price', 'stripe_price_id', 'created_at'
    )
    list_filter = ('service', 'tier_level', 'created_at')
    search_fields = ('service__name', 'stripe_price_id')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Tier Info', {
            'fields': ('service', 'tier_level', 'role','price')
        }),
        ('Stripe Info', {
            'fields': ('stripe_price_id',)
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )