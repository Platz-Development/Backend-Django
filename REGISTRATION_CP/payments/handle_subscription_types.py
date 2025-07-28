import logging
from django.utils import timezone
from decimal import Decimal
from payments.models import (UserPremiumSubscriptionPayment,TutorPremiumSubscriptionPayment)
from subscriptions.models import Subscription,Service
from users.models import User,Tutor
from celery import shared_task

tutoring_logger = logging.getLogger("payments.handle_sub_types.TutoringLogger")

def handle_user_premium_subscription_for_tutoring(user_uid,event, invoice, payment_intent, amount_received, stripe_fee, net_received):
    try:
        metadata = invoice.get('metadata', {})

        if not user_uid:
            tutoring_logger.warning("User Id Not Provided")
            return

        user = User.objects.filter(uid=user_uid).first()
        if not user:
            tutoring_logger.warning(f"User Not Found With Id: {user_uid}")
            return

        user.is_premium_customer = True
        user.save()

        start_date = timezone.now()
        end_date = start_date + timezone.timedelta(days=30)
        
        tutoring_service = Service.objects.get(name='tutoring')

        subscription = Subscription.objects.create(
            user=user,
            role= 'customer',
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            stripe_subscription_id=invoice.get('subscription'),
            stripe_customer_id=invoice.get('customer'),
            stripe_price_id=invoice.get('lines')['data'][0]['price']['id'],
            stripe_checkout_session_id=metadata.get('session_id'),
            amount=Decimal(invoice.get('amount_paid', 0)) / 100,
            billing_interval='monthly',
            service=tutoring_service
        )
        
        
        
        UserPremiumSubscriptionPayment.objects.create(
            user=user,
            subscription=subscription,
            stripe_payment_intent_id=payment_intent.get('id'),
            stripe_subscription_id=invoice.get('subscription'),
            stripe_customer_id=invoice.get('customer'),
            stripe_invoice_id=invoice.get('id'),
            price_id=invoice.get('lines')['data'][0]['price']['id'],
            amount_paid=Decimal(invoice.get('amount_paid', 0)) / 100,
            amount_received_at_stripe=amount_received,
            stripe_fee=stripe_fee,
            net_received_from_stripe=net_received,
            payment_status=invoice.get('status'),
            billing_reason=invoice.get('billing_reason'),
            is_active=True,
            start_date=start_date,
            end_date=end_date,
            cancel_at=invoice.get('cancel_at'),
            cancel_at_period_end=invoice.get('cancel_at_period_end', False),
            canceled_at=invoice.get('canceled_at'),
            metadata=metadata,
            failure_reason=invoice.get('failure_reason'),
        )

        tutoring_logger.info(f"User Premium Subscription Created Successfully For User: {user.email}")

    except Exception as e:
        tutoring_logger.error(f"Error In Handling User Premium Subscription: {str(e)}", exc_info=True)

def handle_tutor_premium_subscription(user_uid,event, invoice, payment_intent, amount_received, stripe_fee, net_received):
    try:
        metadata = invoice.get('metadata', {})

        if not user_uid:
            tutoring_logger.warning(" User uid Not Found In Metadata")
            return

        user = User.objects.filter(uid=user_uid).first()
        if not user:
            tutoring_logger.warning(f"Tutor User Not Found With uid: {user_uid}")
            return

        tutor = Tutor.objects.filter(user=user).first()
        if not tutor:
            tutoring_logger.warning(f"Tutor Profile Not Found For User: {user.email}")
            return

        tutor.is_premium_tutor = True
        tutor.save(update_fields=['is_premium_tutor'])

        start_date = timezone.now()
        end_date = start_date + timezone.timedelta(days=30)
        
        tutoring_service = Service.objects.get(name='tutoring')
        
        subscription = Subscription.objects.create(
            user=user,
            role= 'provider',
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            stripe_subscription_id=invoice.get('subscription'),
            stripe_customer_id=invoice.get('customer'),
            stripe_price_id=invoice.get('lines')['data'][0]['price']['id'],
            stripe_checkout_session_id=metadata.get('session_id'),
            amount=Decimal(invoice.get('amount_paid', 0)) / 100,
            billing_interval='monthly',
            service=tutoring_service
        )
        
        TutorPremiumSubscriptionPayment.objects.create(
            user=user,
            tutor=tutor,
            subscription=subscription,
            stripe_payment_intent_id=payment_intent.get('id'),
            stripe_subscription_id=invoice.get('subscription'),
            stripe_customer_id=invoice.get('customer'),
            stripe_invoice_id=invoice.get('id'),
            price_id=invoice.get('lines')['data'][0]['price']['id'],
            amount_paid=Decimal(invoice.get('amount_paid', 0)) / 100,
            amount_received_at_stripe=amount_received,
            stripe_fee=stripe_fee,
            net_received_from_stripe=net_received,
            payment_status=invoice.get('status'),
            billing_reason=invoice.get('billing_reason'),
            is_active=True,
            start_date=start_date,
            end_date=end_date,
            cancel_at=invoice.get('cancel_at'),
            cancel_at_period_end=invoice.get('cancel_at_period_end', False),
            canceled_at=invoice.get('canceled_at'),
            metadata=metadata,
            failure_reason=invoice.get('failure_reason'),
        )

        tutoring_logger.info(f"Tutor Premium Subscription Created Successfully For User: {user.email}")

    except Exception as e:
        tutoring_logger.error(f"Error In Handling Tutor Premium Subscription: {str(e)}", exc_info=True)
