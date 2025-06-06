from decimal import Decimal
from users.models import User,Availability
from scheduling_stripe.models import TutorLiveClassProfile
from live_class_streaming.models import LiveClassSession
from live_class_streaming.services.live_kit import generate_livekit_join_urls,generate_livekit_session_tokens
from livekit.api import CreateRoomRequest
from get_next_date import get_next_date
from django.utils.timezone import make_aware
from livekit.api import LiveKitAPI
from datetime import datetime
import pytz
import logging
from .models import PaymentForLiveClass,PaymentForCourse,CoursePaymentGroup
from tutor_courses.models import TutorCourses,CoursesPurchased
from .utils import calculate_commission_and_payout_for_tutor,calculate_cp_profit_from_learner




# Set up logging
logger = logging.getLogger(__name__)


def handle_live_class_payment(payment_intent, metadata, net_received_from_stripe, stripe_fee, amount_received_at_stripe): 
        
        selected_availabilities_ids = metadata.get('selected_availabilities_ids', '').split(',')
        live_class_profile_id = metadata.get('live_class_profile_id')
        base_price = Decimal(metadata.get('base_price', 0))
        total_price = Decimal(metadata.get('total_price', 0))
        price_per_hour = Decimal(metadata.get('price_per_hour', 0))
        tutor_currency = metadata.get('tutor_currency')
        learner_currency = metadata.get('learner_currency')
        total_hours = int(metadata.get('total_hours', 0))
        additional_charges = Decimal(metadata.get('additional_charges', 0))
        discount = Decimal(metadata.get('discount', 0))
        #total_converted_price = Decimal(metadata.get('total_converted_price', 0))
        #exchange_rate = Decimal(metadata.get('exchange_rate', 1))
        #converted_base_price = Decimal(metadata.get('converted_base_price', 0))
        #converted_price_per_hour = Decimal(metadata.get('#converted_price_per_hour', 0))
         
        
        live_class_profile = TutorLiveClassProfile.objects.get(pk=live_class_profile_id)
        selected_availabilities = Availability.objects.filter(id__in=selected_availabilities_ids)
        
        tutor = live_class_profile.tutor
        commission = tutor.commission_rate

        cp_profit_from_learner = calculate_cp_profit_from_learner(amount_received_at_stripe, base_price)
        commission_data = calculate_commission_and_payout_for_tutor(commission, base_price)
        cp_commission_from_tutor = commission_data['commission_from_tutor']
        tutor_payout = commission_data['tutor_payout']
        cp_total_profit = cp_profit_from_learner + cp_commission_from_tutor

        payment = PaymentForLiveClass.objects.filter(stripe_payment_id=payment_intent.id).first()
        
        if payment:
            payment.live_class_profile=live_class_profile
            payment.base_price=base_price
            payment.tutor_currency=tutor_currency
            payment.learner_currency=learner_currency
            payment.total_hours=total_hours
            payment.additional_charges=additional_charges
            payment.price_per_hour= price_per_hour
            payment.total_price = total_price
            payment.discount=discount
            payment.cp_profit_from_learner=cp_profit_from_learner
            payment.stripe_fee=stripe_fee
            payment.amount_received_at_stripe=amount_received_at_stripe
            payment.net_received_from_stripe=net_received_from_stripe
            payment.cp_commission_from_tutor = cp_commission_from_tutor
            payment.cp_total_profit=cp_total_profit
            payment.tutor_payout = tutor_payout
            payment.payment_status='succeeded'
            #payment.converted_base_price=converted_base_price
            #payment.total_converted_price=total_converted_price
            #payment.exchange_rate=exchange_rate
            #payment.converted_price_per_hour= converted_price_per_hour
            payment.save()

            logger.info(f"Updated PaymentForLiveClass {payment.id} after successful payment.")

        else:
            logger.error(f"No PaymentForLiveClass object found for PaymentIntent {payment_intent.id}")

        session_ids = []
        for availability in selected_availabilities:
            
            session_date = get_next_date(day_name=availability.day, start_time=availability.start_time,tz_name="Europe/Berlin")
            naive_start_datetime = datetime.combine(session_date, availability.start_time)
            naive_end_datetime = datetime.combine(session_date, availability.end_time)
            
            berlin_tz = pytz.timezone("Europe/Berlin")
            start_datetime = make_aware(naive_start_datetime, timezone=berlin_tz)
            end_datetime = make_aware(naive_end_datetime, timezone=berlin_tz)
            
            session = LiveClassSession.objects.create(
                tutor=payment.tutor,
                learner=payment.learner,
                payment=payment,
                date=session_date,
                scheduled_start_time=start_datetime,
                end_time=end_datetime,
                status="SCHEDULED"  )
            
            session_ids.append(session.id)

            logger.info(f"Live Class Session Created: {session.id}")
            
            #availability.is_booked = True
            #availability.save()
            payment.availabilities.add(availability)
            payment.save()
            
        all_urls =[]                # configure this to send email with the join urls respectively to the learner and tutor
        for sess_id in session_ids:
            urls = generate_livekit_join_urls(session_id=sess_id) # this generates join urls for each session. 1 for tutor and 1 for learner
            session_urls = {
                "session_id": sess_id,
                "learner_url": urls.get("learner_url"),
                "tutor_url": urls.get("tutor_url"),}
            all_urls.append(session_urls)

        logger.info(f"Payment succeeded and Recorded: {payment_intent.id}")
        return all_urls



def handle_course_purchase_payment(payment_intent, metadata, net_received_from_stripe, stripe_fee, amount_received_at_stripe):
         
        learner_email = metadata.get('learner_email')
        course_ids = metadata.get('course_ids', '').split(',')
        base_price = Decimal(metadata.get('base_price', 0))
        total_price = Decimal(metadata.get('total_price', 0))
        tutor_currency = metadata.get('tutor_currency')
        learner_currency = metadata.get('learner_currency')
        additional_charges = Decimal(metadata.get('additional_charges', 0))
        discount = Decimal(metadata.get('discount', 0))
        #total_converted_price = Decimal(metadata.get('total_converted_price', 0))
        #exchange_rate = Decimal(metadata.get('exchange_rate', 1))
        #converted_base_price = Decimal(metadata.get('converted_base_price', 0))
        
     
        learner = User.objects.get(pk=learner_email)
        
        course_payment_group = CoursePaymentGroup.objects.filter(
        learner=learner,
        stripe_payment_intent=payment_intent.id,
        payment_status='pending' ).first()
        
        cp_profit_from_learner = calculate_cp_profit_from_learner(amount_received_at_stripe, base_price)
            
        if course_payment_group:
            course_payment_group.base_price = base_price
            course_payment_group.additional_charges = additional_charges
            course_payment_group.discount = discount
            course_payment_group.total_price = total_price
            course_payment_group.cp_profit_from_learner = cp_profit_from_learner
            course_payment_group.stripe_fee=stripe_fee
            course_payment_group.amount_received_at_stripe=amount_received_at_stripe
            course_payment_group.net_received_from_stripe=net_received_from_stripe
            course_payment_group.payment_status='succeeded'

            for course_id in course_ids: 
                course = TutorCourses.objects.get(pk=course_id)
                course_payment_group.courses.add(course)
        
            course_payment_group.save()


        for course_id in course_ids:
            
            course = TutorCourses.objects.get(pk=course_id)
            learner.additional_charges = additional_charges
            learner.discount = discount
            
            
            course_price = course.price
            additional_charges = learner.additional_charges if hasattr(learner, 'additional_charges') else 20.00
            additional_charges_decimal = Decimal(str(additional_charges))
            course_price_with_add = course_price + (course_price * (additional_charges_decimal / 100))

            discount = learner.discount if hasattr(learner, 'discount') and learner.discount > 0 else 0.00
            discount_decimal = Decimal(str(discount))
            if discount > 0:
               total_course_price = course_price_with_add - (course_price * (discount_decimal / 100))
            
            cp_profit_from_learner = calculate_cp_profit_from_learner(total_course_price, course_price)
         
            tutor = course.tutor
            commission = tutor.commission_rate
            commission_data = calculate_commission_and_payout_for_tutor(commission, course_price)
            cp_commission_from_tutor = commission_data['commission_from_tutor']
            tutor_payout = commission_data['tutor_payout']
            
            cp_total_profit = cp_profit_from_learner + cp_commission_from_tutor

            payment = PaymentForCourse.objects.create(
                stripe_payment_id=payment_intent.id,
                course_payment_group=course_payment_group,
                tutor=tutor,
                learner=learner,
                course_price=course_price,
                tutor_currency=tutor_currency,
                learner_currency=learner_currency,
                additional_charges=additional_charges,
                total_course_price = total_course_price,
                discount=discount,
                cp_profit_from_learner=cp_profit_from_learner,
                cp_commission_from_tutor = cp_commission_from_tutor,
                cp_total_profit=cp_total_profit,
                tutor_payout = tutor_payout,
                payment_status='succeeded',
                #converted_base_price=converted_base_price,
                #total_converted_price=total_converted_price,
                #exchange_rate=exchange_rate,
                )

            course_purchased,created = CoursesPurchased.objects.get_or_create(course=course,learner=learner)
            logger.info(f"Created PaymentForCourse {payment.id} after successful payment.")
            
            
            
        