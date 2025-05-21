from rest_framework import generics, status ,permissions
from rest_framework.permissions import AllowAny , IsAuthenticated 
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, Tutor, Certification, Availability
from .serializers import LearnerSignupSerializer, NewTutorSignupSerializer
from .serializers import ExistingUserTutorSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import MyTokenObtainPairSerializer
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator 
from django.core.mail import send_mail
from django.conf import settings
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import logging
from social_core.backends.google import GoogleOAuth2
from social_django.utils import psa
from .serializers import GoogleAuthSerializer
from django.shortcuts import get_object_or_404
from .models import  Certification, Availability
from .serializers import TutorUpdateSerializer
from permissions import IsTutor, IsTutorOwner
from django.contrib.auth.hashers import check_password
from rest_framework.views import APIView
import json
from rest_framework.parsers import MultiPartParser,FormParser
from .decorators import require_api_key
from django.views.decorators.csrf import csrf_exempt
import requests
from rest_framework.status import HTTP_400_BAD_REQUEST
from django.http import HttpResponse

class LearnerSignUpView(APIView):
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
            'f_name': request.data.get('user[f_name]'),
            'l_name': request.data.get('user[l_name]'),
            'email': request.data.get('user[email]'),
            'password': request.data.get('user[password]'),
            'country':request.data.get('user[country]'),
            'state':request.data.get('user[state]'),
            'city':request.data.get('user[city]'),
            'zip_code':request.data.get('user[zip_code]'),

        }
        university  = request.data.get('university')
        campus = request.data.get('campus')
        course = request.data.get('course')

        data = {
            'user': user_data,
            'university' :university,
            'campus' :campus,
            'course' :course

        }
        email=request.data.get('user[email]')
        
        try:
       
          user = User.objects.get(email__iexact=email)
          if user:
           return Response(f'User with {email} already exists', status=status.HTTP_400_BAD_REQUEST)
        
        except User.DoesNotExist:
          serializer = LearnerSignupSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




   
class TutorSignUpView(APIView):
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
        
        user_data = {
            'f_name': request.data.get('user[f_name]'),
            'l_name': request.data.get('user[l_name]'),
            'email': request.data.get('user[email]'),
            'password': request.data.get('user[password]'),
            'country':request.data.get('user[country]'),
            'state':request.data.get('user[state]'),
            'city':request.data.get('user[city]'),
            'zip_code':request.data.get('user[zip_code]'),

        }

        email=request.data.get('user[email]')
        profile_photo = request.FILES.get('profile_photo')
        address_proof = request.FILES.get('address_proof')
        bio = request.data.get('bio')
        years_of_experience = request.data.get('years_of_experience')
        subjects = json.loads(request.data.get('subjects', '[]'))
        company = request.data.get('company')
        designation = request.data.get('designation')
        tutoring_services_description = request.data.get('tutoring_services_description')

        certifications = []
        for key, file in request.FILES.items():
            if key.startswith('certifications['):
                certifications.append({'certification_image': file})

        availabilities = json.loads(request.data.get('availabilities', '[]'))
        agreed_terms_conditions = request.data.get('agreed_terms_conditions')
        digital_signature = request.data.get('digital_signature')

        data = {
            'user': user_data,
            'profile_photo': profile_photo,
            'address_proof': address_proof,
            'bio': bio,
            'years_of_experience': years_of_experience,
            'subjects': subjects,
            'company': company,
            'designation': designation,
            'tutoring_services_description': tutoring_services_description,
            'certifications': certifications,
            'availabilities': availabilities,
            'agreed_terms_conditions': agreed_terms_conditions,
            'digital_signature': digital_signature,
        }

        try:
            user = User.objects.get(email__iexact=email)
            tutor = Tutor.objects.get(user=user)
            if tutor:
                if not tutor.user.email_verified:
                    return Response(f'Tutor Account with ({email}) Exists. Verification Link Has Been Sent To Your Email. Verify To Login', status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response(f'Tutor Account with ({email}) Already Exists', status=status.HTTP_400_BAD_REQUEST)  
            else:
                 serializer = ExistingUserTutorSerializer(data=data, context={'user': user})
        except User.DoesNotExist:
            serializer = NewTutorSignupSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

#=========================================== Login View Code ======================================================

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class LearnerLoginView(APIView):
    permission_classes = [AllowAny]
     

    def post(self, request, *args, **kwargs):
     email = request.data.get('email')
     password = request.data.get('password')
    
     try:
        user = User.objects.get(email=email)
        if check_password(password, user.password):
            if user.email_verified:
                if user.is_active:
                    if not user.is_google_user and user.is_learner:
                        refresh = MyTokenObtainPairSerializer.get_token(user)
                        return Response({
                            'message': 'Learner login successful',
                            'email': user.email,
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        }, status=status.HTTP_200_OK)
                    else:
                        return Response({"error": "Only Learners can login here"}, status=status.HTTP_403_FORBIDDEN)
                else:
                    return Response({"error": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": "Email is not verified."}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
     except User.DoesNotExist:
        return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)



class TutorLoginView(APIView):
    permission_classes = [AllowAny]


    def post(self, request, *args, **kwargs):
     email = request.data.get('email')
     password = request.data.get('password')
    
     try:
        user = User.objects.get(email=email)
        tutor = Tutor.objects.get(user=user)
        if check_password(password, user.password):
            if user.email_verified and tutor.is_verified:
                if user.is_active:
                    if not user.is_google_user and user.is_tutor:
                        refresh = MyTokenObtainPairSerializer.get_token(user)
                        return Response({
                            'message': 'Tutor login successful',
                            'email': user.email,
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                            'tutor_id':tutor.id,
                        }, status=status.HTTP_200_OK)
                    else:
                        return Response({"error": "Only Learners can login here"}, status=status.HTTP_403_FORBIDDEN)
                else:
                    return Response({"error": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": "Email is not verified."}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
     except User.DoesNotExist:
        return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)


#=========================================== Email Verification View  ======================================================

class EmailVerificationView(APIView):
    def get(self, request, verification_code, *args, **kwargs):
        try:
            user = User.objects.get(verification_code=verification_code)
            user.email_verified = True
            user.is_active = True
            user.verification_code = None  # Clear the verification code after successful verification
            user.save()

            try: 
                tutor=Tutor.objects.get(user=user)
                tutor.is_verified = True
                tutor.save()

            except:
                pass  


            return Response({"message": "Email verified successfully."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Invalid verification code."}, status=status.HTTP_400_BAD_REQUEST)
        
        

#=========================================== Google Signup/Login ======================================================

class GoogleSignupView(APIView):
    @psa('social:complete')
    def post(self, request):
        # Extract data from Google OAuth2 response
        backend = GoogleOAuth2(request)
        user_data = backend.user_data(request.GET.get('code'))

        # Validate and create user using the serializer
        serializer = GoogleAuthSerializer(data=user_data)
        if serializer.is_valid():
            user=serializer.save()
            return Response({
                'message': 'User created successfully',
                'email': user.email,
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GoogleLoginView(APIView):
    @psa('social:complete')
    def post(self, request):
        # Extract data from Google OAuth2 response
        backend = GoogleOAuth2(request)
        user_data = backend.user_data(request.GET.get('code'))

        # Check if the user exists
        email = user_data.get('email')
        try:
            user = User.objects.get(email=email)
            if not user.is_google_user:
               return Response({
                    'message': ''
                }, status=status.HTTP_401_UNAUTHORIZED) 
            if not user.is_learner:
                return Response({
                    'message': ''
                }, status=status.HTTP_401_UNAUTHORIZED)
            return Response({
                'message': 'Login successful',
                'email': user.email,
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({
                'message': 'No account found with this email.'
            }, status=status.HTTP_404_NOT_FOUND)    



#====================================== Forgot Password ===============================================================


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
    
#============================================= Delete Account ===============================================================

class LearnerDeleteAccountView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

#================================================= Tutor Update =======================================================



class TutorUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = TutorUpdateSerializer
    permission_classes = [IsAuthenticated,IsTutor, IsTutorOwner]

    def get_object(self):
        return get_object_or_404(Tutor, user=self.request.user)

class CertificationDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated,IsTutor, IsTutorOwner]

    def get_object(self):
        return get_object_or_404(Certification, id=self.kwargs['pk'], tutor=self.request.user)

class AvailabilityDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated,IsTutor, IsTutorOwner]

    def get_object(self):
        return get_object_or_404(Availability, id=self.kwargs['pk'], tutor=self.request.user)

class TutorDeleteAccountView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated,IsTutor, IsTutorOwner]

    def get_object(self):
        return self.request.user

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
from django.http import HttpResponse
@csrf_exempt
def delete_all_users(request):
    User.objects.all().delete()
    return HttpResponse('All users deleted')
