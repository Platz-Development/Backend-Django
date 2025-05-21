from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from users.models import Tutor,User
from .models import TutorCourses,CoursesPurchased,CourseVideoProgress,SaveForLater,CartItem,Cart, CourseVideo, CourseComment, CourseRating, Cart,CourseCertification
from .serializers import TutorCoursesCreateSerializer,ThumbnailSerializer, CourseCertificationSerializer, CourseCommentSerializer
from .serializers import  CourseRatingSerializer,CourseVideosWatchSerializer,CourseAfterPurchaseSerializer, CourseVideoCreateSerializer,TutorCoursesStats,TutorCourseDisplaySerializer,CourseCommentSerializer
from rest_framework.permissions import IsAuthenticated
from permissions import IsTutor
import logging
from rest_framework.parsers import MultiPartParser,FormParser
from get_timezone import get_timezone_by_country
from my_validators import validate_availabilities
from currency_conversions import convert_currency,get_currency_from_country
from currency_conversions import get_currency_from_country,convert_currency
from django.shortcuts import get_object_or_404
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
import pytz
from secure_file_validation import get_file_hash
from get_timezone import get_timezone_by_country
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from .utils import update_course_progress




logger = logging.getLogger(__name__)


class CourseCertificationAddView(APIView):
    #permission_classes = [IsAuthenticated,IsTutor]

    def get(self, request,email):
       
        tutor = Tutor.objects.select_related('user').get(user__email=email)   
        #tutor = request.user.tutor_profile
        if not tutor.is_premium_user:
            return Response({"error": "Only premium tutors can add certifications."}, status=status.HTTP_403_FORBIDDEN)

        certifications = CourseCertification.objects.all()
        serializer = CourseCertificationSerializer(certifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

#============================= Tutor Course Create View ===========================================

class TutorCoursesCreateView(APIView):
    #permission_classes = [IsAuthenticated, IsTutor]
    parser_classes = (MultiPartParser, FormParser)

    
    def post(self, request,tutor_id):
        
        try:
          tutor = Tutor.objects.get(pk=tutor_id)
        except Tutor.DoesNotExist:
            return Response({"error": "Tutor not found."}, status=status.HTTP_404_NOT_FOUND)

        description = request.data.get('description')
        title = request.data.get('title')
        duration = request.data.get('duration')
        objectives = request.data.get('objectives')
        price = request.data.get('price')
        difficulty_level = request.data.get('difficulty_level')
        certification_id = request.data.get('certification_id')
        subject=request.data.get('subject')
        thumbnail= request.FILES.get('thumbnail')
        preview_video= request.FILES.get('preview_video')
        
        course_data = {
                'description': description,
                'title': title,
                'duration': duration,
                'objectives': objectives,
                'price': price,
                'difficulty_level': difficulty_level,
                'certification_id': certification_id,
                'subject': subject,
                'thumbnail': thumbnail,  
                'preview_video': preview_video, 
            }
       
        try:
            certification=CourseCertification.objects.get(id=certification_id) 
            is_existing_course = TutorCourses.objects.filter(
            tutor=tutor,
            title=title,
            price=price,
            duration=duration,
            difficulty_level=difficulty_level,
            subject=subject,
            certification=certification
            ).exists()

            existing_course = TutorCourses.objects.filter(
            tutor=tutor,
            title=title,
            price=price,
            duration=duration,
            difficulty_level=difficulty_level,
            subject=subject,
            certification=certification
            )

        except:
            certification = None
            is_existing_course = TutorCourses.objects.filter(
            tutor=tutor,
            duration=duration,
            title=title,
            price=price,
            subject=subject,
            difficulty_level=difficulty_level,
            ).exists()
             
            existing_course = TutorCourses.objects.filter(
            tutor=tutor,
            title=title,
            price=price,
            duration=duration,
            difficulty_level=difficulty_level,
            subject=subject,
            )

        if is_existing_course and not CourseVideo.objects.filter(course=existing_course).exists():
              return Response({f'error: You already have a Course with these Details. Continue Videos Uploads from your Dasboard.'},
              status=status.HTTP_400_BAD_REQUEST )
        
        elif is_existing_course and CourseVideo.objects.filter(course=existing_course).exists():
            count =  CourseVideo.objects.filter(course=existing_course).count()
            return Response({f'error: You already have this Course with {count} Videos.'},
            status=status.HTTP_400_BAD_REQUEST )
        
        else:
            course_serializer = TutorCoursesCreateSerializer(data=course_data, context={'tutor': tutor,'certification_id':certification_id})
        
        if course_serializer.is_valid():
            course = course_serializer.save()
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

              video_serializer = CourseVideoCreateSerializer(data=videos_data, many=True,context={'course': course})
              if video_serializer.is_valid():
                video_serializer.save()
                return Response(f'Course Creation and Video Uploads for {title.capitalize()} Successfull ', status=status.HTTP_201_CREATED)
              else:
                return Response(f'Only Course for {title.capitalize()} Could Be Created . Continue Video Uploads From Your Dashboard', status=status.HTTP_201_CREATED)
            else:
                return Response(f'Course Creation for {title.capitalize()} was Successfull. Continue Video Uploads From Your Dashboard', status=status.HTTP_201_CREATED)
        else:
            return Response(course_serializer.errors, status=status.HTTP_400_BAD_REQUEST)



#=========================================== Course Video Upload View =======================================================

class CourseVideoUploadView(APIView):
    #permission_classes = [IsAuthenticated, IsTutor]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request,tutor_id,course_id):

        try:
          tutor = Tutor.objects.get(pk=tutor_id)
        except Tutor.DoesNotExist:
            return Response({"Tutor not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            course = TutorCourses.objects.get(pk=course_id)
        except TutorCourses.DoesNotExist:
            return Response({"Course not found."}, status=status.HTTP_404_NOT_FOUND)


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
                'resolution': request.data.get(f'videos[{i}][resolution]')}
                
                videos_data.append(video_data)

            video_serializer = CourseVideoCreateSerializer(data=videos_data, many=True,context={'course': course})
            if video_serializer.is_valid():              
                video_serializer.save()
                return Response(f' Video Uploads for {course.title.capitalize()} Successfull ', status=status.HTTP_201_CREATED)
            else:
                return Response(video_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                return Response(f'Video Uploads for {course.title.capitalize()} Failed', status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'Please Upload at least 1 Video'},status=status.HTTP_400_BAD_REQUEST)    

#=========================================== Rating Create View =======================================================


class CourseRatingCreateView(APIView):
   # permission_classes = [IsAuthenticated,IsLearner]

    def post(self, request,email, course_id):
        learner = User.objects.get(email=email)
        try:
            course = TutorCourses.objects.get(pk=course_id)
        except TutorCourses.DoesNotExist:
            return Response({"error": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        if CourseRating.objects.filter(course=course, user=learner).exists():
            return Response({"error": "You have already rated this Course."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            course_stats = TutorCoursesStats.objects.get(course=course)
            if not course_stats.learners.filter(email=learner.email).exists():
              return Response({"error": "Only Enrolled Learners Can Rate"}, status=status.HTTP_404_NOT_FOUND)
        except TutorCoursesStats.DoesNotExist:
            return Response({"error": "Course stats not found."}, status=status.HTTP_404_NOT_FOUND)

        rating_value = request.data.get('rating')
        if not (1 <= rating_value <= 5):
            return Response({"error": "Rating must be between 1 star and 5 star."}, status=status.HTTP_400_BAD_REQUEST)

        rating = CourseRating.objects.create(course=course,user=learner,rating=rating_value)

        serializer = CourseRatingSerializer(rating)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

#================================================ Comment Create View ===================================================


class CourseCommentCreateView(APIView):
   # permission_classes = [IsAuthenticated,IsLearner]

    def post(self, request,email, course_id):
        learner = User.objects.get(email=email)
        try:
            course = TutorCourses.objects.get(pk=course_id)
        except TutorCourses.DoesNotExist:
            return Response({"error": "Course not found."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            course_stats = TutorCoursesStats.objects.get(course=course)
            if not course_stats.learners.filter(email=learner.email).exists():
              return Response({"error": "Only Enrolled Learners Can Rate"}, status=status.HTTP_404_NOT_FOUND)
        except TutorCoursesStats.DoesNotExist:
            return Response({"error": "Course stats not found."}, status=status.HTTP_404_NOT_FOUND)

        review_count = CourseComment.objects.filter(course=course, user=learner).count()
        if review_count >= 3:
            return Response(
                {"error": "You have given the maximum no. of reviews per user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        review = request.data.get('review')
        review = CourseComment.objects.create(course=course,user=learner,review=review)
  
        serializer = CourseCommentSerializer(review)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


#======================================= Tutor Course Display Code ====================================


class TutorCourseDisplayView(APIView):
   # permission_classes = [IsAuthenticated,IsLearner]
    def get(self, request,course_id):
        '''email = request.query_params.get('email')  # Extract email from query params
        if not email:
            return Response({"error": "Email parameter is required"}, status=status.HTTP_400_BAD_REQUEST)  '''
        
        
        try:
            course = get_object_or_404(TutorCourses, id=course_id)
            tutor=course.tutor
            stats=TutorCoursesStats.objects.filter(course=course).first()
            learner = User.objects.get(email="deemz@iu.edu.in")
            tutor_country = tutor.user.country
            learner_country = learner.country  
            tutor_currency = get_currency_from_country(tutor_country)
            learner_currency = get_currency_from_country(learner_country)
           
            serializer = TutorCourseDisplaySerializer(tutor, context={'course': course,'stats':stats})
            '''  price_in_tutor_currency = serializer.data['course']['price']
            price_in_tutor_currency_int = int(float(price_in_tutor_currency))
            price_in_learner_currency = convert_currency(price_in_tutor_currency_int,tutor_currency,learner_currency) '''
            serializer_data = serializer.data
            serializer_data['course']['currency'] = tutor_currency 
            subject_name = serializer_data['course']['subject']
            

            courses = TutorCourses.objects.filter(tutor=tutor).exclude(pk=course.id)
            other_courses_from_same_tutor =[]
            for course in courses:
                   tutor_country = 'Germany'
                   tutor_currency = get_currency_from_country(tutor_country)
                   thumbnail_serializer = ThumbnailSerializer(course.thumbnail)
                   other_courses_from_same_tutor.append({
                        'course_id': course.id,
                        'title': course.title,
                        'price': course.price,
                        'tutor_currency':tutor_currency,
                        'thumbnail': thumbnail_serializer.data['thumbnail'],
                        'created_at': course.created_at.strftime('%#d %B, %Y'),  })

            related_courses = TutorCourses.objects.filter(subject=subject_name).exclude(tutor=tutor)
            related_courses_from_other_tutor =[]
            for course in related_courses:
                   tutor_country = 'Germany'
                   tutor_currency = get_currency_from_country(tutor_country)
                   thumbnail_serializer = ThumbnailSerializer(course.thumbnail)
                   related_courses_from_other_tutor.append({
                       'course_id': course.id,
                          'tutor_id' : course.tutor.id,
                          'tutor_name':f"{course.tutor.user.f_name.capitalize()} {course.tutor.user.l_name.capitalize()}",
                          'title': course.title,
                          'price': course.price,
                          'tutor_currency':tutor_currency,
                          'thumbnail': thumbnail_serializer.data['thumbnail'],
                          'created_at': course.created_at.strftime('%#d %B, %Y'),  })  
            
            if len(other_courses_from_same_tutor) > 0:
                message = {'course':serializer.data,
                           'other_courses_from_same_tutor': other_courses_from_same_tutor,
                           'related_courses_from_other_tutor':related_courses_from_other_tutor,
                           }
            else:
                message = serializer.data
                     

            return Response(message, status=status.HTTP_200_OK)
        except Tutor.DoesNotExist:
            return Response({"error": "Tutor not found"}, status=status.HTTP_404_NOT_FOUND)

#===================================== Add To Cart View ============================================== 

class AddToCartView(APIView):
    #permission_classes = [IsAuthenticated]

    def post(self, request,course_id):
        #learner = request.user
        #course_id = request.data.get('course_id')
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing
       
        if not course_id:
            return Response({'error': 'Course ID is required'},status=status.HTTP_400_BAD_REQUEST)

        try:
            course = TutorCourses.objects.get(pk=course_id)
        except TutorCourses.DoesNotExist:return Response( {f'Course not found'},status=status.HTTP_404_NOT_FOUND)

        if course.tutor.user == learner:
            return Response({'error': 'You cannot add your own course to cart'},status=status.HTTP_400_BAD_REQUEST)
        
        saved_item = SaveForLater.objects.filter(learner=learner,course=course)
        
        cart, created = Cart.objects.get_or_create(learner=learner)

        if CartItem.objects.filter(cart=cart, course=course).exists():
            return Response({f'Course {course.title.capitalize()} is already in your CampusPlatz Cart'},status=status.HTTP_400_BAD_REQUEST)
        
        learner_country = learner.country
        learner_timezone = get_timezone_by_country(learner_country)
        learner_tz = pytz.timezone(learner_timezone)
        now_aware = timezone.now().astimezone(learner_tz) 
        CartItem.objects.create(cart=cart, course=course,added_at=now_aware)
        
        if saved_item.exists():
           saved_item.delete()
           return Response(f'Course {course.title.capitalize()} Successfully Moved To your CampusPlatz Cart', status=status.HTTP_201_CREATED)
        else:
           return Response(f'Course {course.title.capitalize()} Successfully Added To your CampusPlatz Cart', status=status.HTTP_201_CREATED)


#===================================== Move To Cart View ============================================== 

class MoveToCartView(APIView):
    #permission_classes = [IsAuthenticated]

    def post(self, request,course_id):
        #learner = request.user
        #course_id = request.data.get('course_id')
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing
       
        if not course_id:
            return Response({'error': 'Course ID is required'},status=status.HTTP_400_BAD_REQUEST)

        try:
            course = TutorCourses.objects.get(pk=course_id)
        except TutorCourses.DoesNotExist:return Response( {f'Course not found'},status=status.HTTP_404_NOT_FOUND)

        if course.tutor.user == learner:
            return Response({'You cannot add your own Course to your CampusPlatz Cart'},status=status.HTTP_400_BAD_REQUEST)
        
        saved_item = get_object_or_404(SaveForLater, learner=learner, course=course)

        if CartItem.objects.filter(cart__learner=learner, course=saved_item.course).exists():
            saved_item.delete() 
            return Response({f'Course {course.title.capitalize()} is already in your CampusPlatz Cart'},status=status.HTTP_400_BAD_REQUEST)

        cart, created = Cart.objects.get_or_create(learner=learner)
        cart_item = CartItem.objects.create(cart=cart, course=saved_item.course)

        saved_item.delete()

        return Response(f'Course {course.title.capitalize()} Successfully Added To your CampusPlatz Cart', status=status.HTTP_201_CREATED)


#===================================== Remove From Cart View ============================================== 


class RemoveFromCartView(APIView):
    #permission_classes = [IsAuthenticated]

    def delete(self, request, item_id, *args, **kwargs):
        #learner = request.user
        #item_id = request.data.get('item_id')
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing
        learner_country = learner.country
        learner_currency = get_currency_from_country(learner_country)

        if not item_id:
            return Response({'error': 'Item ID is required'},status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(learner=learner)
            try:
               cart_item = CartItem.objects.filter(cart=cart).first()
               tutor = cart_item.course.tutor
            except:
               if cart_item==None:
                return Response( 'Your CampusPlatz Cart is Already Empty ',status=status.HTTP_200_OK)
        
            try:
                cart_item = CartItem.objects.select_related('cart', 'cart__learner', 'course').get(
                pk=item_id,
                cart__learner=learner)
            except CartItem.DoesNotExist:return Response( {'error': 'Item not found'},status=status.HTTP_404_NOT_FOUND)

            cart = cart_item.cart
            cart_item.delete()
            cart.refresh_from_db()

            cart_item = CartItem.objects.filter(cart=cart).first()
            if cart_item==None:
                saved_items = SaveForLater.objects.filter(learner=learner).select_related('course')
                saved_data =[]
                for item in saved_items:
                  tutor =item.course.tutor
                  tutor_country = tutor.user.country
                  tutor_currency = get_currency_from_country(tutor_country)
                  serializer = ThumbnailSerializer(item.course.thumbnail)
                  saved_data.append({
                  'id': item.id,
                  'course': {
                  'id': item.course.id,
                  'title': item.course.title,
                  'price': item.course.price,
                  'tutor_currency':tutor_currency,
                  'thumbnail': serializer.data['thumbnail'],
                  'saved_at': item.created_at.strftime('%#d %B, %Y'),
                }}) 
        
                message = {'message':'Your CampusPlatz Cart is Now Empty',
                       'saved_items': {
                            'total_saved_items': len(saved_data),
                            'items': saved_data}}
                return Response(message,status=status.HTTP_200_OK)
          
            tutor_country = tutor.user.country
            tutor_currency = get_currency_from_country(tutor_country)
        
            items_with_prices = []
            base_price = 0

            items = CartItem.objects.filter(cart=cart).order_by('-added_at')
            for item in items:
                original_price = item.course.price
                ''' if tutor_currency == learner_currency:
                   converted_price = original_price
                else:
                   converted_price = convert_currency(tutor_currency,learner_currency,original_price) '''
            
                serializer = ThumbnailSerializer(item.course.thumbnail)
                items_with_prices.append({
                'id': item.id,
                'course_id': item.course.id,
                'title': item.course.title,
                'thumbnail': serializer.data['thumbnail'],
                'original_price': original_price,
               #'converted_price': converted_price,
                'tutor_currency': tutor_currency,
                'added_at': item.added_at.strftime('%#d %B, %Y')  })
            
                base_price += original_price
        
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
            #converted_total_price = convert_currency(total_price_rounded, tutor_currency, learner_currency)         
            #conversion_date = datetime.now().strftime('%Y-%m-%d')
            
            saved_items = SaveForLater.objects.filter(learner=learner).select_related('course')
            saved_data =[]
            for item in saved_items:
               tutor =item.course.tutor
               tutor_country = tutor.user.country
               tutor_currency = get_currency_from_country(tutor_country)
               serializer = ThumbnailSerializer(item.course.thumbnail)
               saved_data.append({
              'id': item.id,
              'course': {
                'id': item.course.id,
                'title': item.course.title,
                'price': item.course.price,
                'tutor_currency':tutor_currency,
                'thumbnail': serializer.data['thumbnail'],
                'saved_at': item.created_at.strftime('%#d %B, %Y'),
            }}) 

            response_data = {
            'cart_id': cart.id,
            'items': items_with_prices,
            'pricing_summary': {
                'subtotal': {'amount': base_price,},
                'additional_charges': {'amount': additional_charges,},
                'discount': {'amount': discount},
                'total': {'amount': total_price,}
            },
            'saved_items': {
                'total_saved_items': len(saved_data),
                'items': saved_data
            },
            'metadata': {
                'tutor_email': tutor.user.email,
                'learner_email':learner.email,
                'tutor_currency': tutor_currency,
                'learner_currency': learner_currency,
                'base_price' : base_price,
                'total_price' : total_price,
                #'exchange_rate': convert_currency(1, tutor_currency, learner_currency),  
                #'conversion_date': conversion_date,
                #'converted_base_price':  converted_base_price,
                'additional_charges':  additional_charges,
                'discount':  discount,
                #'converted_total_price': converted_total_price, 
                #'conversion_date': conversion_date,  
                }}
            
            return Response(response_data)
        
        except Exception as e:
            return Response({'message': str(e),'error': 'Failed to Remove Item from your CampusPlatz Cart'},
                status=status.HTTP_400_BAD_REQUEST)


#================================ Save For Later From Cart View =============================================


class SaveForLaterFromCartView(APIView):
    #permission_classes = [IsAuthenticated]

    def post(self, request, course_id, *args, **kwargs):
        #learner = request.user
        #course_id = request.data.get('course_id')
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing

        if not course_id:
            return Response({'error': 'Course ID is required'},status=status.HTTP_400_BAD_REQUEST)

        try:
            course = TutorCourses.objects.get(pk=course_id)
        except TutorCourses.DoesNotExist:return Response( {f'Course {course.title.capitalize()} not found'},status=status.HTTP_404_NOT_FOUND)
        
        try:
          cart = Cart.objects.get(learner=learner)
        except Cart.DoesNotExist:return Response( 'Your CampusPlatz Cart is Not Found',status=status.HTTP_404_NOT_FOUND)
       
        cart_item = CartItem.objects.filter(cart=cart,course=course).first()

        if cart_item==None:
            return Response({f'Course {course.title.capitalize()} not found in your CampusPlatz cart'},status=status.HTTP_404_NOT_FOUND)

        saved_item, created = SaveForLater.objects.get_or_create(learner=learner,course=cart_item.course)
        if created==False:
            return Response(f'Course {course.title.capitalize()} is Already Saved for Later',status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        cart_item.delete()

        return Response(f'Course {course.title.capitalize()} Saved for Later',status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


#================================ Save For Later View =============================================


class SaveForLaterView(APIView):
    #permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        #learner = request.user
        #course_id = request.data.get('course_id')
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing

        if not course_id:
            return Response({'error': 'Course ID is required'},status=status.HTTP_400_BAD_REQUEST)

        try:
            course = TutorCourses.objects.get(pk=course_id)
        except TutorCourses.DoesNotExist:return Response( {'error': 'Course not found'},status=status.HTTP_404_NOT_FOUND)
        
        saved_item, created = SaveForLater.objects.get_or_create(learner=learner,course=course)
        if created==False:
            return Response(f'Course {course.title.capitalize()} is Already Saved for Later',status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        else:
            return Response(f'Course {course.title.capitalize()} Saved for Later',status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request,course_id, *args, **kwargs):
        #learner = request.user
        #course_id = request.data.get('course_id')
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing

        if not course_id:
            return Response({'error': 'Course ID is required'},status=status.HTTP_400_BAD_REQUEST)
        
        try:
            course = TutorCourses.objects.get(pk=course_id)
        except TutorCourses.DoesNotExist:return Response( {'error': 'Course not found'},status=status.HTTP_404_NOT_FOUND)
        
        saved_item = get_object_or_404(SaveForLater,learner=learner,course=course)
        saved_item.delete()

        return Response({f'Course {course.title.capitalize()} Removed from Saved Items'},status=status.HTTP_200_OK)


#================================ Saved Items Display View =============================================


class SavedCoursesDisplayView(APIView):
    #permission_classes = [IsAuthenticated]

    def get(self, request,):
        #learner = request.user
        #course_id = request.data.get('course_id')
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing
        
        saved_items = SaveForLater.objects.filter(learner=learner).select_related('course')
        saved_data =[]
        for item in saved_items:
               tutor =item.course.tutor
               tutor_country = tutor.user.country
               tutor_currency = get_currency_from_country(tutor_country)
               serializer = ThumbnailSerializer(item.course.thumbnail)
               saved_data.append({
              'id': item.id,
              'course': {
                'id': item.course.id,
                'title': item.course.title,
                'price': item.course.price,
                'tutor_currency':tutor_currency,
                'thumbnail': serializer.data['thumbnail'],
                'saved_at': item.created_at.strftime('%#d %B, %Y'),
            }}) 
        if len(saved_data) > 0:
            message = {'message':'Here are your Saved Courses',
                       'saved_courses': {
                            'total_saved_courses': len(saved_data),
                            'courses': saved_data}}
        else:
            message = {'message':'You Have No Saved Courses Yet.'}
        logger.info(f'Saved-Courses-Display-View = Response Sent Succesfully to {learner.email}')
        return Response(message,status=status.HTTP_200_OK)
        


#================================ Cart Summary View =============================================


class CartDisplayView(APIView):
    #permission_classes = [IsAuthenticated]

    def get(self, request):
        
        #learner = request.user
        learner = User.objects.get(email='deemz@iu.edu.in') # added hardcoding learner email here for testing
        learner_country = learner.country
        learner_currency = get_currency_from_country(learner_country)

        try:
          cart = Cart.objects.get(learner=learner)
        except Cart.DoesNotExist:
            logger.error(f'Cart-Display-View = CampusPlatz Cart is Not Found for {learner.email}')
            return Response( 'Your CampusPlatz Cart is Not Found',status=status.HTTP_404_NOT_FOUND)
        
        
        cart_item = CartItem.objects.filter(cart=cart).first()       
        if cart_item==None:
            saved_items = SaveForLater.objects.filter(learner=learner).select_related('course')
            saved_data =[]
            for item in saved_items:
               tutor =item.course.tutor
               tutor_country = tutor.user.country
               tutor_currency = get_currency_from_country(tutor_country)
               serializer = ThumbnailSerializer(item.course.thumbnail)
               saved_data.append({
              'id': item.id,
              'course': {
                'id': item.course.id,
                'title': item.course.title,
                'price': item.course.price,
                 'tutor_currency':tutor_currency,
                'thumbnail': serializer.data['thumbnail'],
                'saved_at': item.created_at.strftime('%#d %B, %Y'),
            }}) 
        
            message = {'message':'Your CampusPlatz Cart is Empty',
                       'saved_items': {
                            'total_saved_items': len(saved_data),
                            'items': saved_data}}
            logger.info(f'Cart-Display-View = Response Sent Succesfully to {learner.email}')
            return Response(message,status=status.HTTP_200_OK)
        
        tutor = cart_item.course.tutor
        tutor_country = tutor.user.country
        tutor_currency = get_currency_from_country(tutor_country)
        
        items_with_prices = []
        base_price = 0

        items = CartItem.objects.filter(cart=cart).order_by('-added_at')
        for item in items:
            original_price = item.course.price
            '''  if tutor_currency == learner_currency:
                converted_price = original_price
            else:
                converted_price = convert_currency(tutor_currency,learner_currency,original_price) '''
            
            serializer = ThumbnailSerializer(item.course.thumbnail)
            items_with_prices.append({
                'id': item.id,
                'course_id': item.course.id,
                'title': item.course.title,
                'thumbnail': serializer.data['thumbnail'],
                'original_price': original_price,
                #'converted_price': converted_price,
                'tutor_currency': tutor_currency,
                'added_at': item.added_at.strftime('%#d %B, %Y')  })
            
            base_price += original_price
        
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
        #converted_total_price = convert_currency(total_price_rounded, tutor_currency, learner_currency)         
        #conversion_date = datetime.now().strftime('%Y-%m-%d')
        
        saved_items = SaveForLater.objects.filter(learner=learner).select_related('course')
        saved_data =[]
        for item in saved_items:
               tutor =item.course.tutor
               tutor_country = tutor.user.country
               tutor_currency = get_currency_from_country(tutor_country)
               serializer = ThumbnailSerializer(item.course.thumbnail)
               saved_data.append({
              'id': item.id,
              'course': {
                'id': item.course.id,
                'title': item.course.title,
                'price': item.course.price,
                'tutor_currency':tutor_currency,
                'thumbnail': serializer.data['thumbnail'],
                'saved_at': item.created_at.strftime('%#d %B, %Y'),
            }}) 
        
        response_data = {
            'cart_id': cart.id,
            'total_items':len(items_with_prices),
            'items': items_with_prices,
            'pricing_summary': {
                'subtotal':  base_price,
                'additional_charges':  additional_charges,
                'discount':  discount,
                'total':  total_price,
            },
            'saved_items': {
                'total_saved_items': len(saved_data),
                'items': saved_data
            },
            'metadata': {
                'tutor_email':tutor.user.email,
                'learner_email':learner.email,
                'tutor_currency': tutor_currency,
                'learner_currency': learner_currency,
                'base_price' : base_price,
                'total_price' : total_price,
                #'exchange_rate': convert_currency(1, tutor_currency, learner_currency),  
                #'conversion_date': conversion_date,
                #'converted_base_price':  converted_base_price,
                'additional_charges':  additional_charges,
                'discount':  discount,
                #'converted_total_price': converted_total_price, 
                }
            }
        return Response(response_data)
    

#=================================== My Purchases View ==================================
    
class MyPurchasesView(APIView):
    #permission_classes = [IsAuthenticated]

    def get(self, request,):
        #learner = request.user
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing
        
        courses_purchased = CoursesPurchased.objects.filter(learner=learner).select_related('course')
        courses =[]
        for purchase in courses_purchased:
               tutor =purchase.course.tutor
               tutor_country = tutor.user.country
               tutor_currency = get_currency_from_country(tutor_country)
               serializer = ThumbnailSerializer(purchase.course.thumbnail)
               courses.append({
              'purchase_id': purchase.id,
              'course': {
                'course_id': purchase.course.id,
                'title': purchase.course.title,
                'price': purchase.course.price,
                'tutor_currency':tutor_currency,
                'thumbnail': serializer.data['thumbnail'],
                'purchased_at': purchase.purchased_at.strftime('%#d %B, %Y'),
            }}) 
        
        if len(courses) > 0:
            message = {'message':'Here are your Purchased Courses',
                       'purchased_courses': {
                            'total_purchased_courses': len(courses),
                            'courses': courses}}
        else:
            message = {'message':'You Have Not Purchased Any Courses Yet.'}
        return Response(message,status=status.HTTP_200_OK)


#=================================== Course After Purchase Display View ==================================


class CourseAfterPurchaseDisplayView(APIView):
  
    def get(self, request,course_id):
        #learner = request.user
        #course_id = request.data.get('course_id')
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing
        
        try:
            course = TutorCourses.objects.get(pk=course_id)
        except TutorCourses.DoesNotExist:
             return Response({"error": "This Course Does Not Exist."}, status=status.HTTP_404_NOT_FOUND)
        
        if not CoursesPurchased.objects.filter(learner=learner, course=course).exists():
            return Response({"error": "You have Not Purchased This Course."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            course_serializer = CourseAfterPurchaseSerializer(instance=course,context={'learner':learner})
            if course_serializer.is_valid():
               tutor = course.tutor
               courses = TutorCourses.objects.filter(tutor=tutor).exclude(pk=course.id)
               other_courses_from_tutor =[]
               for course in courses:
                   tutor_country = 'Germany'
                   tutor_currency = get_currency_from_country(tutor_country)
                   thumbnail_serializer = ThumbnailSerializer(course.thumbnail)
                   other_courses_from_tutor.append({
                        'course_id': course.id,
                        'title': course.title,
                        'price': course.price,
                        'tutor_currency':tutor_currency,
                        'thumbnail': thumbnail_serializer.data['thumbnail'],
                        'created_at': course.created_at.strftime('%#d %B, %Y'),  }) 
            
            if len(other_courses_from_tutor) > 0:
                message = {'course':course_serializer.data,
                           'other_courses_from_tutor': other_courses_from_tutor}
            else:
                message = course_serializer.data
                    
            return Response(message, status=status.HTTP_200_OK)
        except:
            return Response('Failed To Display Course', status=status.HTTP_400_BAD_REQUEST)


#=================================== Course Videos Watch View ==================================
  

class CourseVideosWatchView(APIView):
    #permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        #learner = request.user
        #course_id = request.data.get('course_id')
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing
        
        try:
            course = TutorCourses.objects.get(pk=course_id)
        except TutorCourses.DoesNotExist:
             return Response({"error": "This Course Does Not Exist."}, status=status.HTTP_404_NOT_FOUND)
        
        if not CoursesPurchased.objects.filter(learner=learner, course=course).exists():
            return Response({"error": "You have Not Purchased This Course."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
           videos = CourseVideo.objects.filter(course=course).order_by('order')
           serializer = CourseVideosWatchSerializer(videos, many=True,context={'learner':learner,'course':course})
           return Response(serializer.data, status=status.HTTP_200_OK)
        except:
             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#=================================== Update Course Video Progress View ==================================
  

class UpdateCourseVideoProgressView(APIView):
    #permission_classes = [IsAuthenticated]

    def post(self, request, video_id):
        #learner = request.user
        learner = User.objects.get(email='deemz@iu.edu.in') # add learner email here for testing
        video = CourseVideo.objects.filter(pk=video_id).first()
        if not video:
            return Response({"error": "Video not found."}, status=404)

        data = request.data
        watched_duration = data.get("watched_duration", 0)
        completed = data.get("completed", False)
        
        tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(tz)

        progress, _ = CourseVideoProgress.objects.get_or_create(learner=learner, video=video)
        progress.watched_duration = max(progress.watched_duration, watched_duration)
        progress.completed = completed
        progress.last_watched = now
        progress.save()

        update_course_progress(learner, video.course,last_video=video)

        return Response({"message": "Progress Updated."})

