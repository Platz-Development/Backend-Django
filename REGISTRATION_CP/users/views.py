from rest_framework import  status ,permissions
from rest_framework.permissions import AllowAny , IsAuthenticated 
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSignupSerializer, NewUserTutorSignupSerializer
from .serializers import ExistingUserTutorSerializer
from .serializers import MyTokenObtainPairSerializer
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator 
from django.core.mail import send_mail
from django.conf import settings
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import logging
from .serializers import GoogleAuthSerializer
from .models import  User,Tutor
from permissions import IsTutor, IsTutorOwner
from django.contrib.auth.hashers import check_password
from rest_framework.views import APIView
import json
from rest_framework.parsers import MultiPartParser,FormParser
#from .decorators import require_api_key
from django.views.decorators.csrf import csrf_exempt
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.utils.timezone import now
import stripe
from subscriptions.models import Service,SubscriptionTier



#========================================== Basic And Premium Customer Signup View ===============================================================

customer_signup_logger = logging.getLogger('users.views.CustomerSignup') 

class NewCustomerSignUpView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

  #  @require_api_key("LEARNER_SIGNUP")
    
    def verify_recaptcha(self, token):

        data = {
            'secret': settings.RECAPTCHA_PRIVATE_KEY,
            'response': token
        }
        response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = response.json()
        return result.get('success', False) and result.get('score', 0) >= 0.5

    def post(self,request):

        '''
        captcha_token = request.data.get('captcha')
        if not captcha_token or not self.verify_recaptcha(captcha_token):
            return Response(
                {"error": "Please enter the valid CAPTCHA"},status=HTTP_400_BAD_REQUEST)'''
        
        user_data = {
            'f_name': request.data.get('f_name'),
            'l_name': request.data.get('l_name'),
            'email': request.data.get('email'),
            'password': request.data.get('password'),
            'country':request.data.get('country'),
            'state':request.data.get('state'),
            'city':request.data.get('city'),
            'zip_code':request.data.get('zip_code'),
            'university' : request.data.get('university'),
            'campus' : request.data.get('campus'),
            'course' : request.data.get('course'),
            'profile_photo' : request.FILES.get('profile_photo'),
            'phone_number': request.data.get('phone_number'),
        
        }
        
        email = user_data.get('email')
        if not email:
            customer_signup_logger.error("Email Field Missing In Request Data.")
            return Response({"error": "Email is Required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if User.objects.filter(email__iexact=email).exists():
                customer_signup_logger.warning(f"Duplicate Signup Attempt From Existing User: {email}")
                return Response({"message": f"User with {email} already exists"}, status=status.HTTP_400_BAD_REQUEST)

            serializer = UserSignupSerializer(data=user_data)
            if serializer.is_valid():
                serializer.save()
                customer_signup_logger.info(f"New User Signed Up : {email}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                customer_signup_logger.warning(f"Validation Failed For Email {email}: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            customer_signup_logger.error(f"Unexpected Error During Signup For {email}: {str(e)}", exc_info=True)
            return Response({"error": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


stripe.api_key = settings.STRIPE_SECRET_KEY

class NewCustomerPremiumSignupView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def verify_recaptcha(self, token):
        data = {
            'secret': settings.RECAPTCHA_PRIVATE_KEY,
            'response': token
        }
        response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = response.json()
        return result.get('success', False) and result.get('score', 0) >= 0.5

    def post(self, request):
        '''
        captcha_token = request.data.get('captcha')
        if not captcha_token or not self.verify_recaptcha(captcha_token):
            return Response(
                {"error": "Please enter the valid CAPTCHA"},status=HTTP_400_BAD_REQUEST)'''
        
        service_id = request.data.get("service_id")
        tier_id = request.data.get("tier_id")

        user_data = {
            'f_name': request.data.get('f_name'),
            'l_name': request.data.get('l_name'),
            'email': request.data.get('email'),
            'password': request.data.get('password'),
            'country': request.data.get('country'),
            'state': request.data.get('state'),
            'city': request.data.get('city'),
            'zip_code': request.data.get('zip_code'),
            'university': request.data.get('university'),
            'campus': request.data.get('campus'),
            'course': request.data.get('course'),
            'profile_photo': request.FILES.get('profile_photo'),
            'phone_number': request.data.get('phone_number'),
        }

        email = user_data.get('email')
        if not email:
            customer_signup_logger.error("Email Field Missing In Request Data.")
            return Response({"error": "Email Is Required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if User.objects.filter(email__iexact=email).exists():
                customer_signup_logger.warning(f"Duplicate Signup Attempt From Existing User: {email}")
                return Response({"message": f"User With {email} Already Exists"}, status=status.HTTP_400_BAD_REQUEST)

            serializer = UserSignupSerializer(data=user_data)
            if serializer.is_valid():
                user = serializer.save(is_premium_customer=False)  # Temporary False
                customer_signup_logger.info(f"New Premium User Registered: {email}")
                
                service = Service.objects.get(id=service_id)
                tier = SubscriptionTier.objects.get(id=tier_id)

                customer = stripe.Customer.create(
                    email= email,
                    metadata={"user_uid": str(user.uid)}
                )

                user.stripe_customer_id = customer.id
                user.save()

                session = stripe.checkout.Session.create(
                    customer=customer.id,
                    payment_method_types=['card'],
                    line_items=[{
                        'price': tier.stripe_price_id,
                        'quantity': 1,
                    }],
                    mode='subscription',
                    subscription_data={
                            'metadata': {
                            'user_uid': str(user.uid),
                            'service':service.name,
                            'type': 'user_premium',
                            'tier_level':tier.tier_level,
                            'tier_name':tier.name,
                            }
                    },
                    metadata={
                        'user_uid': str(user.uid),
                        'type':'user_premium'
                    },
                    success_url=settings.PREMIUM_SUCCESS_URL,
                    cancel_url=settings.PREMIUM_CANCEL_URL,
                )

                customer_signup_logger.info(f"Stripe Checkout Session Created For User: {email}")

                return Response({
                    "message": "User Registered Successfully. Redirecting To Stripe For Premium Payment.",
                    "checkout_session_url": session.url
                }, status=status.HTTP_201_CREATED)

            else:
                customer_signup_logger.warning(f"Validation Failed For Email {email}: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except stripe.StripeError as e:
            customer_signup_logger.error(f"Stripe Error For {email}: {str(e)}")
            return Response({"error": "Stripe Error. Please Try Again."}, status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            customer_signup_logger.error(f"Unexpected Error During Premium Signup For {email}: {str(e)}", exc_info=True)
            return Response({"error": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#============================================== Existing Customer Premium Subscription View ===============================================================

existing_customer_subscription_logger = logging.getLogger("users.views.ExistingCustomerPremiumSubscription")

# Helper to create or retrieve Stripe Customer
def get_or_create_stripe_customer(user):
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=f"{user.f_name} {user.l_name}",
        metadata={"user_id": user.id, "role": "tutor"}
    )
    user.stripe_customer_id = customer.id
    user.save(update_fields=["stripe_customer_id"])
    return customer.id

@method_decorator(ratelimit(key='user_or_ip', rate='5/h', method='POST', block=True), name='dispatch')
class ExistingCustomerPremiumSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        uid = request.data.get('uid')
        service_id = request.data.get("service_id")
        tier_id = request.data.get("tier_id")
        
        try:
            user = User.objects.get(uid=uid)
        except User.DoesNotExist:
            existing_customer_subscription_logger.error(f"User Does Not Exist With uid : {uid}")
            return Response({"error": "User Not Found"}, status=status.HTTP_404_NOT_FOUND)

        
        if user.is_premium_customer:
            existing_customer_subscription_logger.info(f"User Already Subscribed To Premium: {user.id}")
            return Response({"message": "Already A Premium User."}, status=status.HTTP_200_OK)

        try:

            customer_id = get_or_create_stripe_customer(user)

            service = Service.objects.get(id=service_id)
            tier = SubscriptionTier.objects.get(id=tier_id)

            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": tier.stripe_price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                metadata={
                    "user_uid": str(user.uid),
                    "user_email": user.email,
                    "role": "customer",
                    'service':service.name,
                    'type': 'customer_premium',
                    'tier_level':tier.tier_level,
                    'tier_name':tier.name,
                },
                success_url=settings.PREMIUM_SUCCESS_URL,
                cancel_url=settings.PREMIUM_CANCEL_URL,
            )

            existing_customer_subscription_logger.info(f"Stripe Checkout Session Created For User: {user.uid}")
            return Response({"checkout_url": session.url}, status=status.HTTP_200_OK)

        except stripe.StripeError as e:
            existing_customer_subscription_logger.error(f"Stripe Error While Creating Checkout For User {user.uid}: {str(e)}", exc_info=True)
            return Response({"error": "Stripe Error. Please Try Again."}, status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            existing_customer_subscription_logger.exception(f"Unexpected Error During Premium Subscription For {user.uid}")
            return Response({"error": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#============================================= Tutor Signup View ===============================================================


tutor_logger = logging.getLogger('users.views.TutorSignup') 

class NewUserTutorSignupView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        tutor_logger.info("New User Tutor Signup Request Received")

        email = request.data.get('email')
        if not email:
            tutor_logger.warning("Email Not Provided In Signup Request")
            return Response({"message": "Your Email Is Required For Signup"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=email).first()

        if Tutor.objects.filter(user=user).exists():
                tutor_logger.warning(f"Duplicate Signup Attempt From Existing Tutor: {email}")
                return Response({"message": f"Tutor with {email} already exists"}, status=status.HTTP_400_BAD_REQUEST)
       
        user_data = {
            'f_name': request.data.get('f_name'),
            'l_name': request.data.get('l_name'),
            'email': email,
            'password': request.data.get('password'),
            'country': request.data.get('country'),
            'state': request.data.get('state'),
            'city': request.data.get('city'),
            'zip_code': request.data.get('zip_code'),
            'university': request.data.get('university'),
            'campus': request.data.get('campus'),
            'course': request.data.get('course'),
            'profile_photo': request.FILES.get('profile_photo'),
            'phone_number': request.data.get('phone_number'),
        }

        data = {
            'user': user_data,
            'address_proof': request.FILES.get('address_proof'),
            'bio': request.data.get('bio'),
            'years_of_experience': request.data.get('years_of_experience'),
            'subjects': json.loads(request.data.get('subjects', '[]')),
            'company': request.data.get('company'),
            'designation': request.data.get('designation'),
            'tutoring_services_description': request.data.get('tutoring_services_description'),
            'certifications': [
                {'certification_image': file}
                for key, file in request.FILES.items() if key.startswith('certifications[')
            ],
            'availabilities': json.loads(request.data.get('availabilities', '[]')),
            'agreed_terms_conditions': request.data.get('agreed_terms_conditions'),
            'digital_signature': request.data.get('digital_signature')
        }

        serializer = NewUserTutorSignupSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            tutor_logger.info(f"New User Tutor Signup Successful For {email}")
            return Response({"message": "Tutor Signup Successful", "data": serializer.data}, status=status.HTTP_201_CREATED)

        tutor_logger.error(f"New User Tutor Signup Failed For {email}. Errors: {serializer.errors}")
        return Response({"error": "Tutor Signup Failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



class ExistingUserTutorSignupView(APIView):

    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        tutor_logger.info("Existing User Tutor Signup Request Received")

        uid = request.data.get('uid')

        try:
            user = User.objects.get(uid=uid)
        except User.DoesNotExist:
            tutor_logger.error(f"User With UID {uid} Not Found")
            return Response({"error": "User Not Found"}, status=status.HTTP_404_NOT_FOUND)

        if Tutor.objects.filter(user=user).exists():
            tutor = Tutor.objects.get(user=user)
            if not tutor.user.is_user_verified:
                tutor_logger.warning(f"Tutor With {user.email} Exists But Not Verified")
                return Response({"error": f"Tutor Account With {user.email} Exists But Is Not Yet Verified. Please Check Your Email."},status=status.HTTP_400_BAD_REQUEST )
            
            tutor_logger.info(f"Tutor Account With {user.email} Already Exists And Is Verified")
            return Response( {"error": f"Your Tutor Account Already Exists."}, status=status.HTTP_400_BAD_REQUEST )


        data = {
    
            'address_proof': request.FILES.get('address_proof'),
            'bio': request.data.get('bio'),
            'years_of_experience': request.data.get('years_of_experience'),
            'subjects': json.loads(request.data.get('subjects', '[]')),
            'company': request.data.get('company'),
            'designation': request.data.get('designation'),
            'tutoring_services_description': request.data.get('tutoring_services_description'),
            'certifications': [
                {'certification_image': file}
                for key, file in request.FILES.items() if key.startswith('certifications[')
            ],
            'availabilities': json.loads(request.data.get('availabilities', '[]')),
            'agreed_terms_conditions': request.data.get('agreed_terms_conditions'),
            'digital_signature': request.data.get('digital_signature')
        }

        serializer = ExistingUserTutorSerializer(data=data, context={'user': user, 'email': user.email})

        if serializer.is_valid():
            serializer.save()
            tutor_logger.info(f"Existing User Tutor Signup Successful For {user.email}")
            return Response({"message": "Tutor Signup Successful", "data": serializer.data}, status=status.HTTP_201_CREATED)

        tutor_logger.error(f"Existing User Tutor Signup {user.email}. Errors: {serializer.errors}")
        return Response({"error": "Tutor Signup Failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



#============================================== Premium Tutor Subscription View ===============================================================

subscription_logger = logging.getLogger("users.views.ExistingTutorPremiumSubscription")

# Helper to create or retrieve Stripe Customer
def get_or_create_stripe_customer(user):
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=f"{user.f_name} {user.l_name}",
        metadata={"user_id": user.id, "role": "tutor"}
    )
    user.stripe_customer_id = customer.id
    user.save(update_fields=["stripe_customer_id"])
    return customer.id

@method_decorator(ratelimit(key='user_or_ip', rate='5/h', method='POST', block=True), name='dispatch')
class ExistingTutorPremiumSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        uid = request.data.get('uid')
        service_id = request.data.get("service_id")
        tier_id = request.data.get("tier_id")
        
        try:
            user = User.objects.get(uid=uid)
        except User.DoesNotExist:
            subscription_logger.error(f"User Does Not Exist With uid : {uid}")
            return Response({"error": "User Not Found"}, status=status.HTTP_404_NOT_FOUND)

        if not hasattr(user, "tutor"):
            subscription_logger.warning(f"Unauthorized Premium Subscription Attempt By Non-Tutor: {user.email}")
            return Response({"error": "Only Tutors Can Subscribe To Premium."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            tutor = Tutor.objects.get(user=user)
        except Tutor.DoesNotExist:
            subscription_logger.error(f"Tutor Does Not Exist With id : {tutor.id}")
            return Response({"error": "Tutor Not Found"}, status=status.HTTP_404_NOT_FOUND)

        if tutor.is_premium_tutor:
            subscription_logger.info(f"Tutor Already Subscribed To Premium: {tutor.id}")
            return Response({"message": "Already A Premium Tutor."}, status=status.HTTP_200_OK)

        try:

            customer_id = get_or_create_stripe_customer(user)

            service = Service.objects.get(id=service_id)
            tier = SubscriptionTier.objects.get(id=tier_id)

            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": tier.stripe_price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                metadata={
                    "user_uid": str(user.uid),
                    "user_email": user.email,
                    "role": "tutor",
                    'service':service.name,
                    'type': 'tutor_premium',
                    'tier_level':tier.tier_level,
                    'tier_name':tier.name,
                },
                success_url=settings.PREMIUM_SUCCESS_URL,
                cancel_url=settings.PREMIUM_CANCEL_URL,
            )

            subscription_logger.info(f"Stripe Checkout Session Created For Tutor : {tutor.uid}")
            return Response({"checkout_url": session.url}, status=status.HTTP_200_OK)

        except stripe.StripeError as e:
            subscription_logger.error(f"Stripe Error While Creating Checkout For Tutor : {tutor.uid}: {str(e)}", exc_info=True)
            return Response({"error": "Stripe Error. Please Try Again."}, status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            subscription_logger.exception(f"Unexpected Error During Premium Subscription For Tutor : {tutor.uid}")
            return Response({"error": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#============================================== Email Verification View  ======================================================


email_logger = logging.getLogger("users.views.EmailVerification")

class EmailVerificationView(APIView):
    def get(self, request, verification_code, *args, **kwargs):
        email_logger.info("Email Verification Attempt Started")

        try:
            with transaction.atomic():
                user = User.objects.get(verification_code=verification_code)
                user.is_user_verified = True
                user.is_active = True
                user.verification_code = None
                user.save()
                email_logger.info(f"User Verified Successfully: {user.email}")

                tutor_qs = Tutor.objects.filter(user=user)
                if tutor_qs.exists():
                    if tutor_qs.count() > 1:
                        email_logger.warning(f"Multiple Tutors Linked To User {user.email}")
                    tutor = tutor_qs.first()
                    tutor.is_tutor_verified = True
                    tutor.save()
                    email_logger.info(f"Tutor Verified Successfully: {user.email}")

                return Response({"message": "Email Verified Successfully."},status=status.HTTP_200_OK)

        except Exception as e:
            email_logger.exception("Unexpected Error During Email Verification")
            return Response({"error": "An Unexpected Error Occurred."},status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#=========================================== Login View Code ======================================================


login_logger = logging.getLogger('users.Login') 

class CustomerLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        login_logger.info(f"User Login Attempt For {email.title()}")

        try:
            user = User.objects.get(email=email)

            if not check_password(password, user.password):
                login_logger.warning(f"Invalid Password For User {email.title()}")
                return Response({"error": "Invalid Credentials."}, status=status.HTTP_401_UNAUTHORIZED)

            if not user.is_user_verified:
                login_logger.warning(f"Unverified Email For User {email.title()}")
                return Response({"error": "Email Is Not Verified."}, status=status.HTTP_403_FORBIDDEN)

            if not user.is_active:
                login_logger.warning(f"Disabled Account For User {email.title()}")
                return Response({"error": "User Account Is Disabled."}, status=status.HTTP_403_FORBIDDEN)

            if user.is_google_user or not user.is_customer:
                login_logger.warning(f"Invalid Role Attempted Login As User: {email.title()}")
                return Response({"error": "Only Users Can Login Here"}, status=status.HTTP_403_FORBIDDEN)

            user.last_login = now()
            user.save()

            refresh = MyTokenObtainPairSerializer.get_token(user)
            login_logger.info(f"User Login Successful For {email.title()}")

            return Response({
                'message': 'User Login Successful',
                'id': user.id,
                'uid': user.uid,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'is_customer':True,
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            login_logger.warning(f"Login Attempt With Invalid Email {email.title()}")
            return Response({"error": "Invalid Credentials."}, status=status.HTTP_401_UNAUTHORIZED)


class TutorLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        login_logger.info(f"Tutor Login Attempt For {email.title()}")

        try:
            user = User.objects.get(email=email)
            tutor = Tutor.objects.get(user=user)

            if not check_password(password, user.password):
                login_logger.warning(f"Invalid Password For Tutor {email.title()}")
                return Response({"error": "Invalid Credentials."}, status=status.HTTP_401_UNAUTHORIZED)

            if not user.is_user_verified or not tutor.is_tutor_verified:
                login_logger.warning(f"Unverified Email Or Tutor For {email.title()}")
                return Response({"error": "Email Is Not Verified."}, status=status.HTTP_403_FORBIDDEN)

            if not user.is_active:
                login_logger.warning(f"Disabled Account For Tutor {email.title()}")
                return Response({"error": "User Account Is Disabled."}, status=status.HTTP_403_FORBIDDEN)

            if user.is_google_user or not user.is_tutor:
                login_logger.warning(f"Invalid Role Attempted Login As Tutor: {email.title()}")
                return Response({"error": "Only Tutors Can Login Here"}, status=status.HTTP_403_FORBIDDEN)

            user.last_login = now()
            user.save()

            refresh = MyTokenObtainPairSerializer.get_token(user)
            login_logger.info(f"Tutor Login Successful For {email.title()}")

            return Response({
                'message': 'Tutor Login Successful',
                'id': user.id,
                'uid': user.uid,
                'tutor_id': tutor.id,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'is_customer':False,
            }, status=status.HTTP_200_OK)

        except (User.DoesNotExist, Tutor.DoesNotExist):
            login_logger.warning(f"Login Attempt With Invalid Tutor Credentials: {email.title()}")
            return Response({"error": "Invalid Credentials."}, status=status.HTTP_401_UNAUTHORIZED)



#=========================================== Google Signup/Login ======================================================


google_logger = logging.getLogger('users.GoogleLoginSignup')

class GoogleSignupView(APIView):
    
    def post(self, request):
        token = request.data.get('token')
        if not token:
            google_logger.warning("Google ID Token Not Provided In Request.")
            return Response({'error': 'Missing ID token.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID, clock_skew_in_seconds=10 )

            # Validate issuer and email
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                google_logger.error("Invalid Token Issuer.")
                return Response({'error': 'Invalid token issuer.'}, status=status.HTTP_403_FORBIDDEN)

            if not idinfo.get('email_verified'):
                google_logger.warning(f"Email Not Verified For Token: {idinfo.get('email')}")
                return Response({'error': 'Email Not Verified By Google.'}, status=status.HTTP_403_FORBIDDEN)

            # Prepare data
            email = idinfo.get('email')
            user_data = {
                'email': email,
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
            }

            # Check if user already exists
            user_exists = User.objects.filter(email=email).exists()

            if not user_exists:
                # Create new user
                serializer = GoogleAuthSerializer(data=user_data)

                if serializer.is_valid():
                    user = serializer.save()
                    google_logger.info(f"Created New Google User: {user.uid}")
                    created = True
                else:
                    google_logger.error(f"Google Signup Validation Error For {email}: {serializer.errors}")
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Fetch existing user
                user = User.objects.get(email=email)
                google_logger.info(f"Google User Logged In: {email}")
                created = False

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'Account Created Successfully' if created else 'Logged In Successfully',
                'uid': user.uid,
                'id': user.id,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except ValueError as e:
            google_logger.exception("Google Token Verification Failed.")
            return Response({'error': 'Invalid ID Token.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            google_logger.exception("Unexpected Error During Google Signup.")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

@method_decorator(csrf_exempt, name='dispatch')
class GoogleLoginView(APIView):
    def post(self, request):
        token = request.data.get('token')
        if not token:
            google_logger.warning("Google ID Token Not Provided In Request.")
            return Response({'error': 'Missing ID token.'}, status=status.HTTP_400_BAD_REQUEST)

        try:

            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID, clock_skew_in_seconds=10 )

            # Validate issuer and email
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                google_logger.error("Invalid Token Issuer.")
                return Response({'error': 'Invalid token issuer.'}, status=status.HTTP_403_FORBIDDEN)

            if not idinfo.get('email_verified'):
                google_logger.warning(f"Email Not Verified For Token: {idinfo.get('email')}")
                return Response({'error': 'Email Not Verified By Google.'}, status=status.HTTP_403_FORBIDDEN)

            email = idinfo.get('email')

            try:
                user = User.objects.get(email=email)
                if not user.is_google_user:
                    google_logger.warning(f"Non-Google User Account Tried To Log In : {email}")
                    return Response({'error': 'You Have Not Signed Up Via Google. Please Enter Your Email And Password To Log In.'},status=status.HTTP_403_FORBIDDEN)
                
            except User.DoesNotExist:
                google_logger.info(f"Google Login Attempt For Unregistered Email: {email}")
                return Response({'error': 'You Have Not Yet Signed Up Via Google. Please Sign Up First.'},status=status.HTTP_404_NOT_FOUND)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'Logged In Successfully',
                'email': user.email,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            google_logger.exception("Google Token Verification Failed.")
            return Response({'error': 'Invalid ID Token.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            google_logger.exception("Unexpected Error During Google Signup.")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
          

#====================================== Forgot & Reset Password ===============================================================


logger = logging.getLogger(__name__)

@method_decorator(ratelimit(key='ip', rate='3/h', method='POST'), name='post')
class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        logger.info(f"Password reset requested for email: {email}")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'message': 'User with this email does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

        # Send password reset email
        send_mail(
            'Campus Platz - Password Reset Request',
            f'Click the link to reset your password: {reset_link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        return Response({
            'message': 'Password reset link has been sent to your email'
        }, status=status.HTTP_200_OK)


# Reset Password View
class ResetPasswordView(APIView):
    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'message': 'Invalid user or token'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate token
        if not default_token_generator.check_token(user, token):
            return Response({
                'message': 'Invalid or expired token'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update password
        new_password = request.data.get('new_password')
        user.set_password(new_password)
        user.save()

        return Response({
            'message': 'Password has been reset successfully'
        }, status=status.HTTP_200_OK)
    