from django.urls import path
from .views import  NewCustomerSignUpView,ExistingCustomerPremiumSubscriptionView,ExistingTutorPremiumSubscriptionView, NewCustomerPremiumSignupView,NewUserTutorSignupView, ExistingUserTutorSignupView,  TutorLoginView, CustomerLoginView, EmailVerificationView,ForgotPasswordView,ResetPasswordView
#from .views import GoogleLoginView,GoogleSignupView ,TutorUpdateView, CertificationDeleteView,AvailabilityDeleteView,TutorDeleteAccountView
#from.views import delete_all_users
from django.http import HttpResponse

urlpatterns = [


    path('signup/new-customer/', NewCustomerSignUpView.as_view(), name='new_customer-signup'),
    path('signup/new-customer-premium/', NewCustomerPremiumSignupView.as_view(), name='new-customer-premium-signup'),
    path('signup/new-user-tutor/', NewUserTutorSignupView.as_view(), name='new-user-tutor-signup'),
    path('signup/existing-user-tutor/', ExistingUserTutorSignupView.as_view(), name='existing-user-tutor-signup'),
    path('login/customer/', CustomerLoginView.as_view(), name='customer-login'),
    path('login/tutor/', TutorLoginView.as_view(), name='tutor-login'),
    path('verify-email/<str:verification_code>/', EmailVerificationView.as_view(), name='verify-email'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/<uidb64>/<token>/', ResetPasswordView.as_view(), name='reset-password'),
    
    path('subscription/existing-customer-premium/', ExistingCustomerPremiumSubscriptionView.as_view(), name='existing-customer-premium-subscription'),
    path('subscription/existing-tutor-premium/', ExistingTutorPremiumSubscriptionView.as_view(), name='existing-tutor-premium-subscription'),
    path("premium-success/", lambda request: HttpResponse("✅ Premium Signup Successful!")),
    path("premium-cancel/", lambda request: HttpResponse("❌ Premium Signup Cancelled.")),

]