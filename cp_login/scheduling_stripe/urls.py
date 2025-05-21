from django.urls import path
from .views import TutorLiveClassDisplayView,TutorLiveClassCreateView,TutorRatingCreateView,TutorReviewCreateView
from .views import LiveClassCertificationAddView,TutorAvailabilityDisplaytView,CatchUpCourseCreateView, TutorLiveClassSummaryView
from .achievements import BadgeProgressView,ClassCompletionView

urlpatterns = [
     path('tutor/live-class-profile-create/<int:tutor_id>/', TutorLiveClassCreateView.as_view(), name='live-class-profile-create'),
     path('tutor/catch-up-course-create/<int:tutor_id>/', CatchUpCourseCreateView.as_view(), name='catch-up-course-create'),
     path('tutor/display-profile/<int:live_class_profile_id>/', TutorLiveClassDisplayView.as_view(), name='tutor-live-class'),
     path('tutor/live-class-profile/certifications/<int:tutor_id>/', LiveClassCertificationAddView.as_view(), name='live-class-profile-certifications'),
     path('tutor/availabilities/<int:tutor_id>/', TutorAvailabilityDisplaytView.as_view(), name='tutor-availability-display'),
     path('tutor/live-class-summary/<int:live_class_profile_id>/', TutorLiveClassSummaryView.as_view(), name='tutor-live-class-summary'),
     path('tutor/create-rating/<int:live_class_profile_id>/', TutorRatingCreateView.as_view(), name='tutor-rating-create'),
     path('tutor/create-review/<int:live_class_profile_id>/', TutorReviewCreateView.as_view(), name='tutor-review-create'),
     path('tutor/check-badge-progress/<int:tutor_id>/', BadgeProgressView.as_view(), name='check-badge-progress'),
     path('tutor/class-complete-send-mail/<int:live_class_profile_id>/', ClassCompletionView.as_view(), name='class-complete-send-mail'),
              



 
]