from django.urls import path
from .views import (
    TutorCoursesCreateView, TutorCourseDisplayView, CourseCommentCreateView, CourseRatingCreateView,
    AddToCartView,CourseAfterPurchaseDisplayView,MyPurchasesView, CartDisplayView,
    CourseVideoUploadView,RemoveFromCartView,SaveForLaterFromCartView,MoveToCartView,
    SaveForLaterView,SavedCoursesDisplayView,UpdateCourseVideoProgressView,CourseVideosWatchView)

urlpatterns = [
    path('tutor/create-courses/<int:tutor_id>/', TutorCoursesCreateView.as_view(), name='tutor/courses-create'),
    path('tutor/courses/video-upload/<int:tutor_id>/<int:course_id>/', CourseVideoUploadView.as_view(), name='course-video-upload'),
    path('tutor/courses/course-display/<int:course_id>/', TutorCourseDisplayView.as_view(), name='tutor-courses-display'),
    path('tutor/courses/comment/<int:course_id>/', CourseCommentCreateView.as_view(), name='course-comment-create'),
    path('tutor/courses/rating/<int:course_id>/', CourseRatingCreateView.as_view(), name='course-rating-create'),
    path('tutor/courses/add-to-cart/<int:course_id>/', AddToCartView.as_view(), name='add-to-cart'),
    path('tutor/courses/move-to-cart/<int:course_id>/', MoveToCartView.as_view(), name='move-to-cart'),
    path('tutor/courses/save-for-later-from-cart/<int:course_id>/', SaveForLaterFromCartView.as_view(), name='save-for-later-from-cart'),
    path('tutor/courses/save-for-later/<int:course_id>/', SaveForLaterView.as_view(), name='save-for-later'),
    path('tutor/courses/saved-courses-display/', SavedCoursesDisplayView.as_view(), name='saved-items-display'),
    path('my-purchases/', MyPurchasesView.as_view(), name='my-purchases'),
    path('my-purchases/course/display/<int:course_id>/', CourseAfterPurchaseDisplayView.as_view(), name='course-after-purchase-display'),
    path('my-purchases/course/course-videos-watch/<int:course_id>/', CourseVideosWatchView.as_view(), name='course-videos-watch'),
    path('my-purchases/course/update-course-video-progress/<int:video_id>/', UpdateCourseVideoProgressView.as_view(), name='update-course-video-progress'),
    path('tutor/courses/remove-from-cart/<int:item_id>/', RemoveFromCartView.as_view(), name='remove-from-cart'),
    path('tutor/courses/cart-display/', CartDisplayView.as_view(), name='cart-Display'),
]