import stripe
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator

from .handle_subscription_types import (
    handle_user_premium_subscription_for_tutoring,
    handle_tutor_premium_subscription,
)

stripe.api_key = settings.STRIPE_SECRET_KEY
webhook_secret = settings.STRIPE_WEBHOOK_SECRET

stripe_logger = logging.getLogger("payments.views.StripeSubscriptionWebhook")

@method_decorator(csrf_exempt, name='dispatch')
class StripeSubscriptionWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            stripe_logger.info(f"Stripe Event Received: {event['type'].replace('_', ' ').title()}")

        except ValueError as e:
            stripe_logger.error(f"Invalid Payload: {str(e)}", exc_info=True)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.SignatureVerificationError as e:
            stripe_logger.error(f"Signature Verification Failed: {str(e)}", exc_info=True)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            stripe_logger.error(f"Unexpected Error In Webhook: {str(e)}", exc_info=True)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        event_type = event['type']

        
        if event_type in ['invoice.paid', 'checkout.session.completed']:
            try:
                obj = event['data']['object']

                invoice_id = obj.get('invoice') or obj.get('id')  # Covers both cases
                subscription_id = obj.get('subscription')
                customer_id = obj.get('customer')
                payment_intent_id = obj.get('payment_intent')

                invoice = stripe.Invoice.retrieve(invoice_id) if invoice_id else None
                payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id) if payment_intent_id else None
                subscription = stripe.Subscription.retrieve(subscription_id) if subscription_id else None

                # Charge and fee details
                charge_id = invoice.charge if invoice else None
                charge = stripe.Charge.retrieve(charge_id) if charge_id else None

                stripe_fee = None
                amount_received_at_stripe = None
                net_received_from_stripe = None

                if charge and charge.get('balance_transaction'):
                    bt = stripe.BalanceTransaction.retrieve(charge['balance_transaction'])
                    stripe_fee = bt['fee'] / 100
                    amount_received_at_stripe = bt['amount'] / 100
                    net_received_from_stripe = amount_received_at_stripe - stripe_fee

                # Retrieve metadata from subscription safely
                metadata = subscription.get('metadata') or {}

                service = metadata.get('service', '').lower()
                sub_type = metadata.get('type', '').lower()
                user_uid = metadata.get('user_uid', None)

                stripe_logger.info(f"Service Retrieved From Metadata: {service.title()}")

                if service == 'tutoring':
                    stripe_logger.info(f"Subscription Type Retrieved From Metadata: {sub_type.title()}")

                    if sub_type == 'user_premium':
                        try:
                            handle_user_premium_subscription_for_tutoring(
                                user_uid=user_uid,
                                event=event,
                                invoice=invoice,
                                payment_intent=payment_intent,
                                subscription=subscription,
                                amount_received_at_stripe=amount_received_at_stripe,
                                stripe_fee=stripe_fee,
                                net_received_from_stripe=net_received_from_stripe,
                            )
                            stripe_logger.info("Handled User Premium Subscription Successfully")
                        except Exception as e:
                            stripe_logger.error(f"Error Handling User Premium Subscription: {str(e).title()}")

                    elif sub_type == 'tutor_premium':
                        try:
                            handle_tutor_premium_subscription(
                            user_uid=user_uid,
                            event=event,
                            invoice=invoice,
                            payment_intent=payment_intent,
                            subscription=subscription,
                            amount_received_at_stripe=amount_received_at_stripe,
                            stripe_fee=stripe_fee,
                            net_received_from_stripe=net_received_from_stripe,
                        )
                            stripe_logger.info("Handled Tutor Premium Subscription Successfully")
                        except Exception as e:
                            stripe_logger.error(f"Error Handling Tutor Premium Subscription: {str(e).title()}")

                    else:
                        stripe_logger.warning("Subscription Type Not Found In Metadata")


                elif service == 'accommodation':
                    stripe_logger.info("Accommodation Service Handling Placeholder")
                    pass


                elif service == 'jobs':
                    stripe_logger.info("Jobs Service Handling Placeholder")
                    pass


                elif service == 'internships':
                    stripe_logger.info("Internships Service Handling Placeholder")
                    pass


                elif service == 'ielts':
                    stripe_logger.info("IELTS Coaching Service Handling Placeholder")
                    pass


                else:
                    stripe_logger.warning(f"Unknown Or Unsupported Service Received: {service.title()}")

            except Exception as e:
                stripe_logger.error(f"Error Processing Stripe Subscription Webhook: {str(e)}", exc_info=True)
                return Response({"error": "Processing Failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Invoice Payment Failed
        elif event_type == 'invoice.payment_failed':
            stripe_logger.warning("Invoice Payment Failed Event Triggered")

        # Subscription Deleted
        elif event_type == 'customer.subscription.deleted':
            stripe_logger.info("Customer Subscription Deleted Event Triggered")

        # Fallback for all events
        else:
            stripe_logger.info(f"Unhandled Stripe Event Type: {event_type}")

        return Response(status=status.HTTP_200_OK)
