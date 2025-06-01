from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),  
    path('', include('scheduling_stripe.urls')),
    path('', include('payments.urls')), 
    path('', include('scheduling_stripe.urls')), 
    path('', include('live_class_streaming.urls')),
    path('', include('tutor_courses.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)