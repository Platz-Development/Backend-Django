from django.db import models
from django.conf import settings
from users.models import User, Availability,Tutor
from tutor_courses.models import TutorCourses
from scheduling_stripe.models import TutorLiveClassProfile
from simple_history.models import HistoricalRecords
from django.utils import timezone

class PaymentForLiveClass(models.Model):

        
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, related_name='tutor_payments_live_classes',null=True)
    learner = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='learner_payments_live_classes',null=True)
    availabilities = models.ManyToManyField(Availability, related_name='payments')
    live_class_profile = models.ForeignKey(TutorLiveClassProfile, on_delete=models.SET_NULL,null=True ,related_name='payments') 
    tutor_currency = models.CharField(max_length=3,blank=True, null=True)  
    learner_currency = models.CharField(max_length=3,blank=True, null=True) 
    converted_base_price = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    total_hours = models.IntegerField(blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    additional_charges = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    total_price= models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    price_per_hour=models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    converted_price_per_hour=models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    converted_total_price= models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)  
    cp_profit_from_learner = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    cp_commission_from_tutor = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    cp_total_profit= models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    tutor_payout = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    stripe_fee = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    net_received_from_stripe = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)       
    amount_received_at_stripe = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)       
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6,blank=True, null=True)  # Exchange rate used
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    stripe_payment_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    failure_reason = models.TextField(blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"PLC -> {self.id}"



class PaymentForCourse(models.Model):

        
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, related_name='tutor_payments_courses',null=True)
    learner = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='learner_payments_courses',null=True)
    courses = models.ManyToManyField(TutorCourses, related_name='courses')
    tutor_currency = models.CharField(max_length=3,blank=True, null=True)  
    learner_currency = models.CharField(max_length=3,blank=True, null=True) 
    converted_base_price = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    additional_charges = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    total_price= models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    converted_total_price= models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    cp_profit_from_learner = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    cp_commission_from_tutor = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    cp_total_profit= models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    tutor_payout = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    stripe_fee = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)  
    net_received_from_stripe = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)       
    amount_received_at_stripe = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)        
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6,blank=True, null=True)  
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    stripe_payment_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    failure_reason = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"PCP -> {self.id}"

