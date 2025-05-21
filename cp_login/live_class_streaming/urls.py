from django.urls import path
from .views import LiveKitWebhookView,LiveKitClassJoinAPIView,QoSTelemetryAPIView,StartLivekitRecordingAPIView,StopLivekitRecordingAPIView


urlpatterns = [
    path('livekit/webhook/', LiveKitWebhookView.as_view(), name='livekit-webhook'),
    path('livekit/join-live-class/', LiveKitClassJoinAPIView.as_view(), name='livekit-join-live-class'),
    path('livekit/start-recording/', StartLivekitRecordingAPIView.as_view(), name='livekit-start-recording'),
    path('livekit/stop-recording/', StopLivekitRecordingAPIView.as_view(), name='livekit-stop-recording'),

 
 ]