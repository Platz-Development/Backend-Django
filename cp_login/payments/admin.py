from django.contrib import admin
from import_export.admin import ExportActionMixin
from simple_history.admin import SimpleHistoryAdmin
from .models import PaymentForLiveClass,PaymentForCourse

@admin.register(PaymentForLiveClass)
class PaymentForLiveClassAdmin(ExportActionMixin, SimpleHistoryAdmin):
    list_display = (
        'id', 'tutor', 'learner','live_class_profile__title','stripe_payment_id', 'base_price' ,'total_price',
        'cp_total_profit', 'payment_status','created_at'
    )
    list_filter = ('payment_status', 'created_at', )
    search_fields = (
        'tutor__user__email', 'learner__email', 'stripe_payment_id','payment_status', 'live_class_profile__title'
    )
    autocomplete_fields = (
        'tutor', 'learner', 'live_class_profile', 'availabilities'
    )
    readonly_fields = (
    'created_at',
    'stripe_payment_id', 'amount_received_at_stripe', 'stripe_fee', 'net_received_from_stripe',
    'cp_profit_from_learner', 'cp_commission_from_tutor', 'cp_total_profit',)

    fieldsets = (
        ('Payments For Live Classes', {
            'fields': ['tutor', 'learner', 'live_class_profile', 'availabilities']
        }),
        ('Currencies & Exchange', {
            'classes': ('collapse',),
            'fields': [
                'tutor_currency', 'learner_currency', 'exchange_rate',
                'converted_base_price', 'converted_total_price',
                'converted_price_per_hour'
            ]
        }),
        ('Price Breakdown', {
            'fields': [
                'price_per_hour','total_hours', 'base_price', 
                'additional_charges', 'discount', 'total_price',
                
            ]
        }),

        ('CampusPlatz Profits ', {
            'fields': ['cp_profit_from_learner', 'cp_commission_from_tutor','cp_total_profit' ]
        }),

        ('Stripe Details ', {
            'fields': ['stripe_payment_id','amount_received_at_stripe','stripe_fee','net_received_from_stripe','tutor_payout','payment_status', 'created_at']
        }),
        
        
    )


@admin.register(PaymentForCourse)
class PaymentForCourseAdmin(ExportActionMixin, SimpleHistoryAdmin):
    list_display = (
        'id', 'tutor', 'learner','stripe_payment_id','base_price' , 'total_price',
        'cp_total_profit','payment_status', 'created_at',
    )
    list_filter = ('payment_status', 'created_at', )
    search_fields = (
        'tutor__user__email', 'learner__email', 'stripe_payment_id','courses'
    )
    autocomplete_fields = (
        'tutor', 'learner', 'courses'
    )
    readonly_fields = (
    'created_at',
    'stripe_payment_id', 'amount_received_at_stripe', 'stripe_fee', 'net_received_from_stripe',
    'cp_profit_from_learner', 'cp_commission_from_tutor', 'cp_total_profit',)

    fieldsets = (
        ('Payments For Courses', {
            'fields': ['tutor', 'learner', 'courses']
        }),
        ('Currencies & Exchange', {
            'classes': ('collapse',),
            'fields': [
                'tutor_currency', 'learner_currency', 'exchange_rate',
                'converted_base_price', 'converted_total_price',
                
            ]
        }),
        ('Price Breakdown', {
            'fields': [
                 'base_price', 'additional_charges', 'discount', 'total_price',
                ]
        }),
        ('CampusPlatz Profits ', {
            'fields': ['cp_profit_from_learner', 'cp_commission_from_tutor','cp_total_profit' ]
        }),
        ('Stripe Details ', {
            'fields': ['stripe_payment_id','amount_received_at_stripe','stripe_fee','net_received_from_stripe','tutor_payout','payment_status', 'created_at']
        }),
        
        
        
    )
