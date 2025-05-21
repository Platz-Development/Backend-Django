import stripe
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging
from decimal import Decimal
from users.models import Tutor, User, Availability
from django.core.exceptions import ValidationError
from django.db import transaction
import os
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from celery import shared_task
from .models import PaymentForLiveClass,PaymentForCourse
from .handle_payment_types import handle_course_purchase_payment,handle_live_class_payment
from live_class_streaming.models import LiveClassSession
from tutor_courses.models import TutorCourses

# Set up logging
logger = logging.getLogger(__name__)


stripe.api_key ='sk_test_51RFbQ6Gace72vhR6HdxrPMjFj1KvWrZBinls5sGwDmCdzLlJhxdrt0jKMK72T5ERW88WzHNLvLxabm0T3bwH3iQ500rL00WMzF'


class LiveClassPaymentIntent(APIView):

    stripe.api_key ='sk_test_51RFbQ6Gace72vhR6HdxrPMjFj1KvWrZBinls5sGwDmCdzLlJhxdrt0jKMK72T5ERW88WzHNLvLxabm0T3bwH3iQ500rL00WMzF'

    def post(self, request, *args, **kwargs):
       
        live_class_profile_id = request.data.get('live_class_profile_id')
        tutor_email = request.data.get('tutor_email')
        learner_email = request.data.get('learner_email')
        selected_availabilities_ids = request.data.get('selected_availabilities_id', [])
        price_per_hour = Decimal(request.data.get('price_per_hour', 0))
        total_hours = Decimal(request.data.get('total_hours', 0))
        base_price = Decimal(request.data.get('base_price', 0))
        tutor_currency = request.data.get('tutor_currency')
        learner_currency = request.data.get('learner_currency')
        additional_charges = Decimal(request.data.get('additional_charges', 20))
        discount = Decimal(request.data.get('discount', 0))
        total_price = Decimal(request.data.get('total_price', 0))
        #conversion_date = request.data.get('conversion_date')
        #converted_total_price = Decimal(request.data.get('converted_total_price', 0))
        #exchange_rate = Decimal(request.data.get('exchange_rate', 1))
        #converted_price_per_hour = request.data.get('converted_price_per_hour')
        #converted_base_price = Decimal(request.data.get('converted_base_price', 0))
         
        required_fields =[tutor_email, learner_email, selected_availabilities_ids, price_per_hour, total_hours, 
                          base_price, tutor_currency, learner_currency, total_price,
                          live_class_profile_id]
        
        for field in required_fields:
          if field not in required_fields:
            logger.error(f"Live-Class-Payment-Intent = Missing field {field}  in the request")
            return Response({"error": "All fields are required"},status=status.HTTP_400_BAD_REQUEST)
       
        try:
            tutor = Tutor.objects.select_related('user').get(user__email=tutor_email)
            learner = User.objects.get(email=learner_email)
        except (Tutor.DoesNotExist, User.DoesNotExist) as e:
            logger.error(f"Live-Class-Payment-Intent = Invalid tutor or learner : {e}")
            return Response({"error": "Invalid tutor or learner."},status=status.HTTP_400_BAD_REQUEST)

        try:
            selected_availabilities = Availability.objects.filter(id__in=selected_availabilities_ids)
            if len(selected_availabilities) != len(selected_availabilities_ids):
                logger.error("Live-Class-Payment-Intent = Invalid Selected Availabilities IDs")
                return Response({"error": "Invalid Selected Availabilities "},status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Live-Class-Payment-Intent = Error fetching selected availabilities: {e}")
            return Response({"error": "Invalid Selected Availabilities "},status=status.HTTP_400_BAD_REQUEST)

        metadata = {
            'live_class_profile_id': str(live_class_profile_id),
            'tutor_email': str(tutor_email),  # Use ID instead of email
            'learner_email': str(learner_email),  # Use ID instead of email
            'selected_availabilities_ids': ','.join(map(str, selected_availabilities_ids)),
            'price_per_hour': str(price_per_hour),
            'total_hours': str(total_hours),
            'base_price': str(base_price),
            'tutor_currency': tutor_currency,
            'learner_currency': learner_currency,
            'additional_charges': str(additional_charges),
            'discount': str(discount),
            'total_price': str(total_price),
            #'exchange_rate': str(exchange_rate),
            #'converted_price_per_hour': str(converted_price_per_hour),
            #'converted_base_price': str(converted_base_price),
            #'converted_total_price': str(converted_total_price)
            #'conversion_date': str(conversion_date), 
        }

        logger.info(f"Live-Class-Payment-Intent = Data From Request Received Successfully")

        # Convert the total price to cents (Stripe requires amounts in cents)
        total_price_cents = int(total_price * 100)
      
        try:
            with transaction.atomic():
                payment_intent = stripe.PaymentIntent.create(
                    amount=total_price_cents,
                    currency=learner_currency.lower(),  # Ensure currency is in lowercase
                    metadata=metadata,
                    payment_method_types=['card'],
                    description=f"Payment for tutor {tutor.user.email} by learner {learner.email}",
                )
                logger.info(f"Live-Class-Payment-Intent = PaymentIntent created successfully: {payment_intent.id}")

        except stripe.StripeError as e:
            logger.error(f"Live-Class-Payment-Intent = Stripe error while creating PaymentIntent: {e}")
            return Response({"error": "Payment processing failed. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except ValidationError as e:
            logger.error(f"Live-Class-Payment-Intent = Validation error: {e}")
            return Response({"error": "Invalid data provided"},status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Live-Class-Payment-Intent = Unexpected error: {e}")
            return Response({"error": "An unexpected error occurred"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

        PaymentForLiveClass.objects.create(
        tutor=tutor,
        learner=learner,
        stripe_payment_id=payment_intent.id,
        payment_status='pending' )


        response_data = {
            'client_secret': payment_intent.client_secret,
            'payment_intent_id': payment_intent.id,
            'total_price': total_price,
            'currency': learner_currency,
            'metadata': metadata,  # Ensure no PII is exposed
        }
        logger.info(f"Live-Class-Payment-Intent = PaymentIntent Sent Successfully: {payment_intent.id}")

        return Response(response_data, status=status.HTTP_201_CREATED)
    

#============================================== Stripe Webhook ================================================================

logger = logging.getLogger(__name__)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, 'whsec_sVjxCAmvQvhLmScJAoZIlrshcaayNJvl'
        )
    except ValueError as e:
        logger.error(f"Stripe-Webhook => Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':

        payment_intent = event["data"]["object"]
        metadata = payment_intent.get("metadata", {})

        stripe_fee = None
        net_received_from_stripe = None
        amount_received_at_stripe = None

        if 'latest_charge' in payment_intent and payment_intent['latest_charge']:
            charge_id = payment_intent['latest_charge']
            try:
                charge = stripe.Charge.retrieve(charge_id)
                balance_txn_id = charge.get('balance_transaction')

                if balance_txn_id:
                    try:
                       balance_transaction = stripe.BalanceTransaction.retrieve(balance_txn_id)
                       amount_received_at_stripe = balance_transaction.amount / 100  # total amount Stripe processed
                       stripe_fee = balance_transaction.fee / 100          # Stripe's fee
                       net_received_from_stripe = (balance_transaction.amount - balance_transaction.fee) / 100 
                       logger.info(f"✅ Stripe Payment Received: {amount_received_at_stripe} , Fee: {stripe_fee}, Net: {net_received_from_stripe}")
                    except stripe.StripeError as e:
                       logger.warning(f"⚠️ Could Not Retrieve Balance Transaction: {e}")
                else:
                    logger.warning("⚠️ No Balance Transaction ID Found On The Charge.")

            except stripe.StripeError as e:
                logger.warning(f"⚠️ Could Not Retrieve Charge: {e}")
        else:
            logger.warning(f"⚠️ PaymentIntent {payment_intent.id} Has No Associated Charge.")

        if amount_received_at_stripe is None:
            try:
                amount_received_at_stripe = float(payment_intent['metadata'].get('total_price', 0))
                logger.info(f"🔁 Fallback: Amount Received At Stripe From metadata For Payment Intent: {payment_intent.id} - {amount_received_at_stripe}")
            except Exception as e:
                logger.error(f"⚠️ Could Not Get Total Price From Metadata: {e}")
                amount_received_at_stripe = 0.0

        logger.info(f" Net Received From Stripe for {payment_intent.id} : {net_received_from_stripe}")
         
        if "live_class_profile_id" in metadata:
            all_urls =  handle_live_class_payment(payment_intent, metadata, net_received_from_stripe, stripe_fee, amount_received_at_stripe)
        elif "course_ids" in metadata:
            handle_course_purchase_payment(payment_intent, metadata, net_received_from_stripe, stripe_fee, amount_received_at_stripe)
        else:
            logger.warning("Unhandled Payment Intent due to Unknown Payment type.")
        print(f"all_urls = {all_urls}")
        return HttpResponse({f"message":"Payment Was Succesfully Completed And Your Live Classes Are Scheduled"},status=status.HTTP_200_OK)


    elif event['type'] == 'payment_intent.payment_failed':

        payment_intent = event["data"]["object"]
        metadata = payment_intent.get("metadata", {})
        failure_reason = payment_intent.get("last_payment_error", {}).get("message", "Unknown Reason")

        if "live_class_profile_id" in metadata:
            payment = PaymentForLiveClass.objects.filter(stripe_payment_id=payment_intent.id).first()
        
            if payment:
               payment.payment_status = 'failed'
               payment.failure_reason = failure_reason
               payment.save()
               
        elif "course_ids" in metadata:
            payment = PaymentForCourse.objects.filter(stripe_payment_id=payment_intent.id).first()
            
            if payment:
               payment.payment_status = 'failed'
               payment.failure_reason = failure_reason
               payment.save()

        else:
            logger.warning("Unhandled Payment Intent due to Unknown Payment type.")

        logger.error(f"Payment failed: {payment_intent.id}")
        return HttpResponse({f"message":"Payment Failed...Please Try Again"},status=status.HTTP_200_OK)
      

    elif event['type'] == 'charge.refunded':
      
        charge = event['data']['object']
        payment_intent_id = charge.get('payment_intent')
        metadata = charge.get('metadata', {})
        charge_id = charge.get('id')

        if not payment_intent_id:
            logger.warning(f"Refunded Charge {charge_id} Missing payment_intent.")
            return HttpResponse({f"error":"Refund Could Not Be Initiated. Please Contact Customer Support"},status=status.HTTP_400_BAD_REQUEST)
        
        if "live_class_profile_id" in metadata:
            payment = PaymentForLiveClass.objects.filter(stripe_payment_id=payment_intent_id).first()
            
            if payment:
                payment.payment_status = 'refunded'
                payment.availabilities.update(is_booked=False)
                payment.save()
                logger.info(f"Payment Refunded For Charge ({charge_id}) With Payment ID {payment_intent_id}") 
                print(f"✅ Refund created successfully for PaymentIntent: {payment_intent_id}")  
                return HttpResponse({f"message":"Payment is Succesfully Refunded And Your Live Classes Are Cancelled"},status=status.HTTP_200_OK)
            else:
                return HttpResponse({f"message":"There Is No Payment Record For A Refund"},status=status.HTTP_404_NOT_FOUND)
              
        elif "course_ids" in metadata:
            payment = PaymentForCourse.objects.filter(stripe_payment_id=payment_intent_id).first()
            
            if payment:
                payment.payment_status = 'refunded'
                payment.save()
                logger.info(f"Payment Refunded For Charge ({charge_id}) With Payment ID {payment_intent_id}")
                print(f"✅ Refund created successfully for PaymentIntent: {payment_intent_id}")
                return HttpResponse({f"message":"Payment is Succesfully Refunded And Your Live Classes Are Cancelled"},status=status.HTTP_200_OK)
            else:
                return HttpResponse({f"message":"There Is No Payment Record For A Refund"},status=status.HTTP_404_NOT_FOUND)
            


#============================== Course Purchase Payment Intent Creation ========================== 


class CoursePurchasePaymentIntent(APIView):

    stripe.api_key ='sk_test_51RFbQ6Gace72vhR6HdxrPMjFj1KvWrZBinls5sGwDmCdzLlJhxdrt0jKMK72T5ERW88WzHNLvLxabm0T3bwH3iQ500rL00WMzF'

    def post(self, request, *args, **kwargs):
        # Extract data from the request
        course_ids = request.data.get('course_ids',[])
        learner_email = request.data.get('learner_email')
        tutor_email = request.data.get('tutor_email')
        base_price = Decimal(request.data.get('base_price', 0))
        tutor_currency = request.data.get('tutor_currency')
        learner_currency = request.data.get('learner_currency')
        additional_charges = Decimal(request.data.get('additional_charges', 20))
        discount = Decimal(request.data.get('discount', 0))
        total_price = Decimal(request.data.get('total_price', 0))
        
        required_fields =[ learner_email, base_price, tutor_currency,
                         learner_currency, total_price,course_ids,discount,additional_charges,
                         ]
        
        for field in required_fields:
          if field not in required_fields:
            logger.error(f"Missing field {field}  in the request")
            return Response({"error": "All fields are required"},status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"Course-Purchase-Payment-Intent = Data From Request Received ")

        try:
            courses = TutorCourses.objects.filter(id__in=course_ids)
            if len(courses) != len(course_ids):
                logger.error("Course-Purchase-Payment-Intent = Invalid Selected Courses IDs")
                return Response({"error": "Invalid Selected Courses "},status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Course-Purchase-Payment-Intent = Error Fetching Selected Courses: {e}")
            return Response({"error": "Invalid Selected Courses "},status=status.HTTP_400_BAD_REQUEST)

        metadata = {
            'course_ids':','.join(map(str, course_ids)),
            'learner_email': str(learner_email), 
            'base_price': str(base_price),
            'tutor_currency': tutor_currency,
            'learner_currency': learner_currency,
            'additional_charges': str(additional_charges),
            'discount': str(discount),
            'total_price': str(total_price),
            }
        
        logger.info(f"Course-Purchase-Payment-Intent =  Metadata added Successfully")

        # Convert the total price to cents (Stripe requires amounts in cents)
        total_price_cents = int(total_price * 100)

        try:
            with transaction.atomic():
                payment_intent = stripe.PaymentIntent.create(
                    amount=total_price_cents,
                    currency=learner_currency.lower(),  # Ensure currency is in lowercase
                    metadata=metadata,
                    payment_method_types=['card'],
                    description=f"Payment for tutor {','.join(map(str, course_ids))} by learner {learner.email}",
                )
                logger.info(f"Course-Purchase-Payment-Intent = Payment Intent Created Successfully: {payment_intent.id}")

        except stripe.StripeError as e:
            logger.error(f"Course-Purchase-Payment-Intent = Stripe error while creating PaymentIntent: {e}")
            return Response({"error": "Payment processing failed. Please try again later."},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except ValidationError as e:
            logger.error(f"Course-Purchase-Payment-Intent = Validation error: {e}")
            return Response({"error": "Invalid data provided"},status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Course-Purchase-Payment-Intent = Unexpected error: {e}")
            return Response({"error": "An unexpected error occurred"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        for course_id in course_ids:
            try: 
               learner = User.objects.get(pk=learner_email)
               course = TutorCourses.objects.get(pk=course_id)
            except (User.DoesNotExist, TutorCourses.DoesNotExist) as e:
                if isinstance(e, User.DoesNotExist):
                  logger.error(f"User not found (Learner: {learner_email}): {str(e)}")
                else:
                  logger.error(f"Tutor Course not found with ID: {course_id}")

            tutor = course.tutor

            PaymentForCourse.objects.create(
            tutor=tutor,
            learner=learner,
            stripe_payment_id=payment_intent.id,
            payment_status='pending' )

        response_data = {
            'client_secret': payment_intent.client_secret,
            'payment_intent_id': payment_intent.id,
            'total_price': total_price,
            'currency': learner_currency,
            'metadata': metadata,  
        }

        logger.info(f"Course-Purchase-Payment-Intent = Sucessfully Created : {payment_intent}")

        return Response(response_data, status=status.HTTP_201_CREATED)
    
