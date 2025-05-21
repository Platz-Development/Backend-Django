from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from .models import Tutor, TutorLiveClassProfile,CatchUpCourseVideo,CatchUpCourseForLiveClass, Availability , LiveClassCertification , Review,Rating,TutorLiveClassStats
from .serializers import TutorLiveClassDisplaySerializer,CatchUpCourseDisplaySerializer,CatchUpCourseCreateSerializer,CatchUpCourseVideoCreateSerializer,TutorLiveClassCreateSerializer, LiveClassCertificationSerializer
from rest_framework.permissions import AllowAny , IsAuthenticated 
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from permissions import IsLearner, IsTutor
from django.conf import settings
from .serializers import TutorAvailabilityDisplaySerializer ,LiveClassRatingSerializer,LiveClassReviewSerializer
import pytz
import json
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from pytz.exceptions import UnknownTimeZoneError
from rest_framework.throttling import UserRateThrottle
from decimal import Decimal, ROUND_HALF_UP
from users.models import User
from currency_conversions import convert_currency,get_currency_from_country
import logging
from currency_conversions import get_currency_from_country,convert_currency
from rest_framework.parsers import MultiPartParser,FormParser
from get_timezone import get_timezone_by_country
from my_validators import validate_availabilities
from .serializers import ThumbnailSerializer

logger = logging.getLogger(__name__)




class LiveClassCertificationAddView(APIView):
    permission_classes = [IsAuthenticated,IsTutor]

    def get(self, request,tutor_id):
       
        tutor = Tutor.objects.get(tutor_id=tutor_id)   
        if not tutor.is_premium_user:
            return Response({"error": "Only premium tutors can add certifications."}, status=status.HTTP_403_FORBIDDEN)

        certifications = LiveClassCertification.objects.all()
        serializer = LiveClassCertificationSerializer(certifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


     
 #====================================== Tutor Live Class Profile Create Code ====================================   


class TutorLiveClassCreateView(APIView):
     
     #   permission_classes = [IsAuthenticated,IsTutor] 

    def post(self, request,tutor_id):

        tutor = Tutor.objects.get(pk=tutor_id)  
        description = request.data.get('description')
        title = request.data.get('title')
        price_per_hour = request.data.get('price')
        topics_covered = request.data.get('topics_covered')
        difficulty_level = request.data.get('difficulty_level')
        certification_id = request.data.get('certification_id')
        subject=request.data.get('subject')
        thumbnail= request.FILES.get('thumbnail')

        profile_data = {
                'title':title,
                'description': description,
                'topics_covered':topics_covered,
                'price_per_hour': price_per_hour,
                'difficulty_level': difficulty_level,
                'certification_id': certification_id,
                'subject': subject,
                'thumbnail': thumbnail,   
            }

        try:
            certification=LiveClassCertification.objects.get(id=certification_id) 
            existing_profile = TutorLiveClassProfile.objects.filter(
            tutor=tutor,
            title=title,
            price_per_hour=price_per_hour,
            difficulty_level=difficulty_level,
            subject=subject,
            certification=certification
            ).exists()

        except:
            certification = None
            existing_profile = TutorLiveClassProfile.objects.filter(
            tutor=tutor,
            title=title,
            price_per_hour=price_per_hour,
            subject=subject,
            difficulty_level=difficulty_level,
            ).exists()

        if existing_profile:
            return Response({'error': 'You already have a live class profile with these details.'},
            status=status.HTTP_400_BAD_REQUEST )
        else:
            serializer = TutorLiveClassCreateSerializer(data=profile_data, context={'tutor': tutor})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



#============================= Catch Up Course Create View ===========================================

class CatchUpCourseCreateView(APIView):

    #permission_classes = [IsAuthenticated, IsTutor]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request,tutor_id ):
        
        try:
            tutor = Tutor.objects.get(pk=tutor_id) 
        except Tutor.DoesNotExist:
            return Response({'error':f'Tutor Does Not Exist'},status=status.HTTP_404_NOT_FOUND)

        live_class_profiles = TutorLiveClassProfile.objects.filter(tutor=tutor)
        profiles_of_tutor =[]
        for profile in live_class_profiles:
            tutor_country = 'Germany'
            tutor_currency = get_currency_from_country(tutor_country)
            thumbnail_serializer = ThumbnailSerializer(profile.thumbnail)
            profiles_of_tutor.append({
                'live_class_profile_id': profile.id,
                    'title':profile.title,
                    'subject': profile.subject,
                    'price_per_hour': profile.price_per_hour,
                    'tutor_currency':tutor_currency,
                    'difficulty_level':profile.difficulty_level,
                    'thumbnail': thumbnail_serializer.data['thumbnail'], }) 
                 
            if live_class_profiles.exists() :
                message = {'profiles_of_tutor':profiles_of_tutor
                           }
            else:
                message = "You Have No Live Classes Yet. Hope To See You Create One Soon!!"
        return Response(message, status=status.HTTP_200_OK)

    def post(self, request,tutor_id):
        
        try:
          tutor = Tutor.objects.get(pk=tutor_id)
        except Tutor.DoesNotExist:
            return Response({"error": "Tutor not found."}, status=status.HTTP_404_NOT_FOUND)
        
        live_class_profile_id = request.data.get('live_class_profile_id')
        description = request.data.get('description')
        title = request.data.get('title')
        duration = request.data.get('duration')
        objectives = request.data.get('objectives')
        difficulty_level = request.data.get('difficulty_level')
        thumbnail= request.FILES.get('thumbnail')
        preview_video= request.FILES.get('preview_video')
        
        try:
          live_class_profile = TutorLiveClassProfile.objects.get(pk=live_class_profile_id)
        except TutorLiveClassProfile.DoesNotExist:
            return Response({"error": "Live Class not found."}, status=status.HTTP_404_NOT_FOUND)
        
        course_data = {
                'description': description,
                'title': title,
                'duration': duration,
                'objectives': objectives,
                'difficulty_level': difficulty_level,
                'thumbnail': thumbnail,  
                'preview_video': preview_video, 
            }
        try:
            is_existing_course = CatchUpCourseForLiveClass.objects.filter(
            live_class_profile=live_class_profile,
            title=title,
            duration=duration,
            difficulty_level=difficulty_level,
            ).exists()

            existing_course = CatchUpCourseForLiveClass.objects.filter(
            live_class_profile=live_class_profile,
            title=title,
            duration=duration,
            difficulty_level=difficulty_level,
            )

        except:
            is_existing_course = CatchUpCourseForLiveClass.objects.filter(
            live_class_profile=live_class_profile,
            duration=duration,
            title=title,
            objectives=objectives,
            difficulty_level=difficulty_level,
            ).exists()

            existing_course = CatchUpCourseForLiveClass.objects.filter(
            live_class_profile=live_class_profile,
            duration=duration,
            title=title,
            objectives=objectives,
            difficulty_level=difficulty_level,
            )

        if is_existing_course and not CatchUpCourseVideo.objects.filter(course=existing_course).exists():
              return Response({f'error: You already have a Catch Up Course with these Details. Continue Videos Uploads from your Dasboard.'},
              status=status.HTTP_400_BAD_REQUEST )
        
        elif is_existing_course and CatchUpCourseVideo.objects.filter(course=existing_course).exists():
            count =  CatchUpCourseVideo.objects.filter(course=existing_course).count()
            return Response({f'error: You already have this Course with {count} Videos.'},
            status=status.HTTP_400_BAD_REQUEST )
        
        else:
            course_serializer = CatchUpCourseCreateSerializer(data=course_data, context={'tutor': tutor,'live_class_profile':live_class_profile})
        
        if course_serializer.is_valid():
            catch_up_course = course_serializer.save()
            videos_data = []
            video_count = int(request.data.get('video_count', 0))
            
            if video_count: 
              for i in range(video_count):
                video_data = {
                'video_title': request.data.get(f'videos[{i}][video_title]'),
                'description': request.data.get(f'videos[{i}][description]'),
                'order': request.data.get(f'videos[{i}][order]'),
                'video_file': request.FILES.get(f'videos[{i}][video_file]'),
                'thumbnail': request.FILES.get(f'videos[{i}][thumbnail]'),
                'duration': request.data.get(f'videos[{i}][duration]'),
                'resolution': request.data.get(f'videos[{i}][resolution]'),}
                
                videos_data.append(video_data)

              video_serializer = CatchUpCourseVideoCreateSerializer(data=videos_data, many=True,context={'catch_up_course': catch_up_course})
              if video_serializer.is_valid():
                video_serializer.save()
                return Response(f'Course Creation and Video Uploads for {title.capitalize()} Successfull ', status=status.HTTP_201_CREATED)
              else:
                return Response(f'Only Course for {title.capitalize()} Could Be Created . Continue Video Uploads From Your Dashboard', status=status.HTTP_201_CREATED)
            else:
                return Response(f'Course Creation for {title.capitalize()} was Successfull. Continue Video Uploads From Your Dashboard', status=status.HTTP_201_CREATED)
        else:
            return Response(course_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#======================================= Tutor Live Class Profile Display Code ====================================


class TutorLiveClassDisplayView(APIView):
   # permission_classes = [IsAuthenticated,IsLearner]
    def get(self, request,live_class_profile_id):
        '''email = request.query_params.get('email')  # Extract email from query params
        if not email:
            return Response({"error": "Email parameter is required"}, status=status.HTTP_400_BAD_REQUEST)  '''
        
        try:
            #learner = request.user
            
            live_class_profile = get_object_or_404(TutorLiveClassProfile, pk=live_class_profile_id)
            tutor = live_class_profile.tutor 
            stats=TutorLiveClassStats.objects.filter(live_class_profile=live_class_profile).first()
            learner = User.objects.get(email="deemz@iu.edu.in")
            tutor_country = tutor.user.country
            learner_country = learner.country  
            tutor_currency = get_currency_from_country(tutor_country)
            learner_currency = get_currency_from_country(learner_country)
           
            serializer = TutorLiveClassDisplaySerializer(instance=tutor, context={'live_class_profile': live_class_profile,'stats':stats})
            ''' price_in_tutor_currency = serializer.data['live_class_profile']['price']
            price_in_tutor_currency_int = int(float(price_in_tutor_currency))
            price_in_learner_currency = convert_currency(price_in_tutor_currency_int,tutor_currency,learner_currency)'''
            serializer_data = serializer.data
            serializer_data['live_class_profile']['currency'] = tutor_currency
            subject_name = serializer_data['live_class_profile']['subject']
            

            catch_up_courses = CatchUpCourseForLiveClass.objects.filter(live_class_profile=live_class_profile)
            if catch_up_courses.exists():
                catch_up_course_serialzer = CatchUpCourseDisplaySerializer(catch_up_courses,many=True).data
            else:
                catch_up_course_serialzer = []
            live_class_profiles = TutorLiveClassProfile.objects.filter(tutor=tutor).exclude(id=live_class_profile.id)
            other_profiles_from_same_tutor =[]
            for profile in live_class_profiles:
                tutor_country = 'Germany'
                tutor_currency = get_currency_from_country(tutor_country)
                thumbnail_serializer = ThumbnailSerializer(profile.thumbnail)
                other_profiles_from_same_tutor.append({
                    'profile_id': profile.id,
                        'title':profile.title,
                        'subject': profile.subject,
                        'price_per_hour': profile.price_per_hour,
                        'tutor_currency':tutor_currency,
                        'difficulty_level':profile.difficulty_level,
                        'thumbnail': thumbnail_serializer.data['thumbnail'], }) 
            
            related_live_class_profiles = TutorLiveClassProfile.objects.filter(subject=subject_name).exclude(tutor=tutor)
            related_profiles_from_different_tutors =[]
            for profile in related_live_class_profiles:
                tutor_country = 'Germany'
                tutor_currency = get_currency_from_country(tutor_country)
                thumbnail_serializer = ThumbnailSerializer(profile.thumbnail)
                related_profiles_from_different_tutors.append({
                    'profile_id': profile.id,
                        'tutor_id' : profile.tutor.id,
                        'tutor_name':f"{profile.tutor.user.f_name.capitalize()} {profile.tutor.user.l_name.capitalize()}",
                        'title':profile.title,
                        'subject': profile.subject,
                        'price_per_hour': profile.price_per_hour,
                        'tutor_currency':tutor_currency,
                        'difficulty_level':profile.difficulty_level,
                        'thumbnail': thumbnail_serializer.data['thumbnail'], }) 
                
             
            if live_class_profiles.exists() or related_live_class_profiles.exists():
                message = {'profile':serializer.data,
                           "catch_up_courses": catch_up_course_serialzer,
                           'other_profiles_from_same_tutor': other_profiles_from_same_tutor,
                           'related_profiles_from_different_tutors':related_profiles_from_different_tutors
                           }
            else:
                message = serializer.data
            
            return Response(message, status=status.HTTP_200_OK)
        except Tutor.DoesNotExist:
            return Response({"error": "Tutor not found"}, status=status.HTTP_404_NOT_FOUND)
        
#========================================= Availability List View =========================================================

class TutorAvailabilityDisplaytView(APIView):
     # permission_classes = [IsAuthenticated,IsLearner]
    
    def get(self,request,tutor_id):

        tutor = Tutor.objects.get(pk=tutor_id) 
        tutor_country = tutor.user.country
        '''
        learner_timezone = request.query_params.get('timezone', 'UTC')
        try:
            pytz.timezone(learner_timezone)  # Validate timezone
        except UnknownTimeZoneError:'''
        tutor_timezone = 'Europe/Berlin'
        learner_timezone = 'Europe/Berlin'
        pytz.timezone(learner_timezone)
        pytz.timezone(tutor_timezone)

        # Get the current day and the next 6 days
        today = timezone.now().date()
        days = [today + timedelta(days=i) for i in range(7)]
        day_names = [day.strftime('%A') for day in days]

        # Fetch availabilities for the tutor within the next 7 days
        availabilities = Availability.objects.filter(
            tutor=tutor,
            day__in=day_names,
            is_booked=False
        )

        # Group availabilities by day
        grouped_availabilities = {}
        for day in day_names:
            day_availabilities = availabilities.filter(day=day).order_by('start_time')
            serializer = TutorAvailabilityDisplaySerializer(
                day_availabilities, many=True, 
            )
            grouped_availabilities[day] = serializer.data

        return Response(grouped_availabilities, status=status.HTTP_200_OK)
    

#======================================= Live Class Summary =========================================================

class TutorLiveClassSummaryView(APIView):

    #  permission_classes = [IsAuthenticated,IsLearner]
    throttle_classes = [UserRateThrottle]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, live_class_profile_id):
        
        '''
        learner_timezone = request.query_params.get('timezone', 'UTC')
        try:
            pytz.timezone(learner_timezone)  # Validate timezone
        except UnknownTimeZoneError:'''

        #learner = request.user
        learner = User.objects.get(email="deemz@iu.edu.in")
        learner_country = learner.country
        learner_currency = get_currency_from_country(learner_country)
        learner_timezone = 'Europe/Berlin'
        pytz.timezone(learner_timezone)
       
        # Get the selected availability IDs from the request
        selected_availability_ids = json.loads(request.data.get('selected_availabilities', '[]'))  
        
        try:
            live_class_profile = TutorLiveClassProfile.objects.get(pk = live_class_profile_id)
            price_per_hour = live_class_profile.price_per_hour
            tutor=live_class_profile.tutor
            tutor_country=tutor.user.country
            tutor_currency = get_currency_from_country(tutor_country)
            tutor_timezone = 'Europe/Berlin'
            pytz.timezone(tutor_timezone)
       
        except:
            return Response(
                {'error': 'Tutor Profile Does not Match'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not selected_availability_ids:
            return Response(
                {'error': 'No availabilities selected.Please select at least 1'},
                status=status.HTTP_400_BAD_REQUEST
            )

        selected_availabilities = validate_availabilities(selected_availability_ids,tutor,learner_timezone,tutor_timezone)
    
  
        response_data = {}
    
        if selected_availabilities['booked'] or selected_availabilities['invalid']:
            if selected_availabilities['booked']:
              response_data['booked_availabilities'] = {
                'message': 'The following slots are already booked',
                'slots': selected_availabilities['booked']}
              
            if selected_availabilities['invalid']:
              response_data['invalid_availabilities'] = {
                'message': 'The following slots are invalid',
                'slots': selected_availabilities['invalid']
            }
        
            logger.warning(f"Availability validation issues: {response_data}")
            return Response(
            response_data,
            status=status.HTTP_400_BAD_REQUEST)
        

        total_hours = len(selected_availabilities['valid'])
        base_price = price_per_hour * total_hours
        base_price = float(base_price) 
        #converted_base_price = convert_currency(base_price, tutor_currency, learner_currency)
        base_price = Decimal(str(base_price))

        additional_charges = learner.additional_charges if hasattr(learner, 'additional_charges') else 20.00
        additional_charges_decimal = Decimal(str(additional_charges))
        base_price_with_add = base_price + (base_price * (additional_charges_decimal / 100))

        discount = learner.discount if hasattr(learner, 'discount') and learner.discount > 0 else 0.00
        discount_decimal = Decimal(str(discount))
        if discount > 0:
            total_price = base_price_with_add - (base_price * (discount_decimal / 100))

      
        
        total_price_rounded = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)  
        base_price = float(base_price)
        total_price_rounded=float(total_price_rounded)
        price_per_hour=float(price_per_hour)

        #converted_price_per_hour =  convert_currency(price_per_hour, tutor_currency, learner_currency)
        #converted_total_price = convert_currency(total_price_rounded, tutor_currency, learner_currency)
        #conversion_date = datetime.now().strftime('%Y-%m-%d')
        
        response = {
       'tutor_name': f'{tutor.user.f_name.capitalize()} {tutor.user.l_name.capitalize()}',
       'selected_availabilities': [
        {
        'id': item['id'],
        'day': item['day'],
        'start_time': item['start_time'],  
        'end_time': item['end_time']      
        }
        for item in selected_availabilities['valid']
        ],
       'pricing_summary':{
       'price_per_hour': price_per_hour,
       'total_hours':           total_hours,
       'base_price':  base_price, 
       'additional_charges':    additional_charges,
       'discount':               discount if discount > 0 else 0.00,
       'total_price':            total_price,
        },
       'metadata': {
                'live_class_profile_id': live_class_profile_id,
                'tutor_email': tutor.user.email,
                'learner_email':learner.email,
                'tutor_currency': tutor_currency,
                'selected_availabilities_ids': [ item['id'] for item in selected_availabilities['valid']],
                'learner_currency': learner_currency,
                'base_price' : base_price,
                'additional_charges':  additional_charges,
                'discount':  discount,
                'total_price' : total_price,
                'price_per_hour': price_per_hour, 
                #'converted_price_per_hour': converted_price_per_hour,
                #'exchange_rate': convert_currency(1, tutor_currency, learner_currency),  
                #'conversion_date': conversion_date,
                #'converted_base_price':  converted_base_price,
                #'converted_total_price': converted_total_price, 
                }}
       
        return Response(response, status=status.HTTP_200_OK)
        
   
#=========================================== Rating Create View =======================================================


class TutorRatingCreateView(APIView):
   # permission_classes = [IsAuthenticated,IsLearner]

    def post(self, request, live_class_profile_id):
        learner = User.objects.get(email="test1@iu.study.de")
        try:
            live_class_profile = TutorLiveClassProfile.objects.get(pk=live_class_profile_id)
        except TutorLiveClassProfile.DoesNotExist:
            return Response({"error": "Live class profile not found."}, status=status.HTTP_404_NOT_FOUND)

        if Rating.objects.filter(live_class_profile=live_class_profile, user=learner).exists():
            return Response({"error": "You have already rated this live class profile."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            live_class_stats = TutorLiveClassStats.objects.get(live_class_profile=live_class_profile)
            if not live_class_stats.learners.filter(email=learner.email).exists():
              return Response({"error": "Only Enrolled Learners Can Rate"}, status=status.HTTP_404_NOT_FOUND)
        except TutorLiveClassStats.DoesNotExist:
            return Response({"error": "Live class stats not found."}, status=status.HTTP_404_NOT_FOUND)

        rating_value = request.data.get('rating')
        if not (1 <= rating_value <= 5):
            return Response({"error": "Rating must be between 1 star and 5 star."}, status=status.HTTP_400_BAD_REQUEST)

        rating = Rating.objects.create(
            live_class_profile=live_class_profile,
            user=learner,
            rating=rating_value
        )

        serializer = LiveClassRatingSerializer(rating)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

#================================================ Review Create View ===================================================


class TutorReviewCreateView(APIView):
   # permission_classes = [IsAuthenticated,IsLearner]

    def post(self, request, live_class_profile_id):
        learner = User.objects.get(email="test1@iu.study.de")
        try:
            live_class_profile = TutorLiveClassProfile.objects.get(pk=live_class_profile_id)
        except TutorLiveClassProfile.DoesNotExist:
            return Response({"error": "Live class profile not found."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            live_class_stats = TutorLiveClassStats.objects.get(live_class_profile=live_class_profile)
            if not live_class_stats.learners.filter(email=learner.email).exists():
              return Response({"error": "Only Enrolled Learners Can Rate"}, status=status.HTTP_404_NOT_FOUND)
        except TutorLiveClassStats.DoesNotExist:
            return Response({"error": "Live class stats not found."}, status=status.HTTP_404_NOT_FOUND)

        review_count = Review.objects.filter(live_class_profile=live_class_profile, user=learner).count()
        if review_count >= 3:
            return Response(
                {"error": "You have given the maximum no. of reviews per user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        review = request.data.get('review')
        review = Review.objects.create(
            live_class_profile=live_class_profile,
            user=learner,
            review=review
        )
  
        serializer = LiveClassReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

