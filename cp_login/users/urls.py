from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from .views import MyTokenObtainPairView, LearnerSignUpView, TutorSignUpView, TutorLoginView, LearnerLoginView, EmailVerificationView,ForgotPasswordView,ResetPasswordView
from .views import GoogleLoginView,GoogleSignupView , LearnerDeleteAccountView,  TutorUpdateView, CertificationDeleteView,AvailabilityDeleteView,TutorDeleteAccountView
from.views import delete_all_users
from django.views.decorators.csrf import csrf_exempt


urlpatterns = [

    
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/google/signup/', GoogleSignupView.as_view(), name='google_signup'),
    path('auth/google/login/', GoogleLoginView.as_view(), name='google_login'),
    
    
    path('signup/learner/', LearnerSignUpView.as_view(), name='learner-signup'),
    path('signup/tutor/', TutorSignUpView.as_view(), name='tutor-signup'),
    path('login/learner/', LearnerLoginView.as_view(), name='learner-login'),
    path('login/tutor/', TutorLoginView.as_view(), name='tutor-login'),
    path('verify-email/<str:verification_code>/', EmailVerificationView.as_view(), name='verify-email'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', ResetPasswordView.as_view(), name='reset_password'),
    
        
    path('tutor/profile/', TutorUpdateView.as_view(), name='tutor-profile-update'),
    path('tutor/certifications/<int:pk>/', CertificationDeleteView.as_view(), name='certification-delete'),
    path('tutor/availabilities/<int:pk>/', AvailabilityDeleteView.as_view(), name='availability-delete'),
    path('tutor/delete-account/', TutorDeleteAccountView.as_view(), name='tutor-delete-account'),
    path('delete-accounts/', csrf_exempt(delete_all_users), name='tutor-delete-account'),
    

]