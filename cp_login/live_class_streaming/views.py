from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import timedelta
import logging
import hmac
import hashlib
import json
from django.conf import settings
from .models import LiveClassSession, SessionTelemetry, SessionRecording
from .services.daily_co_service import DailyCoService
from .tasks import notify_participants, download_recording
from .services.daily_co_service import prepare_daily_co_fallback
from get_timezone import get_timezone_by_country
import pytz
from urllib.parse import unquote, parse_qs ,urlparse
from live_class_streaming.services.live_kit import generate_livekit_session_tokens,generate_livekit_join_urls,start_livekit_recording
import hashlib
from django.views.decorators.csrf import csrf_exempt
from .models import SessionEventLog
import asyncio
import aiohttp
from livekit import api
from .services.egress_recording import start_composite_egress, stop_egress
from datetime import datetime
import base64
from live_class_streaming.models import LiveKitClassJoinURL
from dateutil.parser import isoparse
from .services.live_kit import create_livekit_room_sync
from users.models import User
from django.utils.decorators import method_decorator
import jwt
from .utils import safe_title_for_recording
from .services.cloudflare_r2 import generate_r2_signed_url

GERMANY_TZ = pytz.timezone('Europe/Berlin')
BUFFER_MINUTES = 10  

logger = logging.getLogger(__name__)

class LiveKitClassJoinAPIView(APIView):
    
    #permission_classes = [IsAuthenticated]
    
    def generate_signature(self, key, expires_at_str): 
        data = f"{key}{expires_at_str}"
        return hmac.new(settings.SECRET_KEY.encode(),data.encode(),hashlib.sha256).hexdigest()

    def post(self, request):
      
      try:  
        
        try:
            learner_email = "deemz@iu.edu.in"
            user = User.objects.get(email=learner_email)
            key = request.GET.get('key')
            expires_at_str = request.GET.get('expires_at')
            signature = request.GET.get('signature')
    
            # Validate that key, expires_at, and signature are present
            if not all([key, expires_at_str, signature]):
                logger.error(f"LiveKit-Class-Join-API = Invalid or Not All URL parameters ")
                return Response({"error": "Invalid Join URL"},status=status.HTTP_400_BAD_REQUEST)
            
            expected_signature = self.generate_signature(key, expires_at_str)
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning(f"LiveKit-Class-Join-API = Invalid Signature ")
                return Response({"error": "Invalid Signature in URL"}, status=status.HTTP_400_BAD_REQUEST)

            expires_at = isoparse(expires_at_str)
            now = timezone.now().astimezone(GERMANY_TZ)
            if now > expires_at:
                logger.error(f"LiveKit-Class-Join-API = URL Has Expired ")
                return Response({"error": "URL has expired"}, status=status.HTTP_400_BAD_REQUEST)
               
        except Exception as e:
            logger.error(f"LiveKit-Class-Join-API = URL Verification Failed: {str(e)}")
            return Response({"error": f"URL Verification Failed: {str(e)}"},status=status.HTTP_400_BAD_REQUEST)
        
        try:
            url = LiveKitClassJoinURL.objects.get(key=key)
        except LiveKitClassJoinURL.DoesNotExist :
            logger.warning(f"LiveKit-Class-Join-API = Join URL Does Not Exist ")
            return Response({f" Join URL Does Not Exist"},status=status.HTTP_404_NOT_FOUND)
        
        session = url.session

        if user not in [session.tutor.user, session.learner]:
            logger.error(f"Live-Class-Join-API = UnAuthorized Participant Tried to Join. Session ID : {session.id}")
            return Response({"error": "You are not an Authorized Participant"}, status=status.HTTP_403_FORBIDDEN)

        if not (session.payment and session.payment.payment_status == "succeeded"):
            logger.error(f"Live-Class-Join-API = Payment is not completed")
            return Response( {"error": "Payment is not completed"},  status=status.HTTP_402_PAYMENT_REQUIRED)
        
        if not session.status == "SCHEDULED":
            if not session.status == "ONGOING":
                logger.error(f"Live-Class-Join-API = Session Is Not Scheduled")
                return Response( {"error": "Session Is Not Scheduled"},  status=status.HTTP_402_PAYMENT_REQUIRED)
        
        if user == session.tutor.user:
           
           tutor_timezone = get_timezone_by_country('Germany')
           now = timezone.now().astimezone(pytz.timezone(tutor_timezone))
           tutor_scheduled_start = session.scheduled_start_time.astimezone(pytz.timezone(tutor_timezone))
           '''
           if session.date != now.date():
               logger.error(f"Live-Class-Join-API = {session.tutor.user.email} Tried To Join On Wrong Date ")
               return Response({"error": f"This Live Class starts on {session.date.strftime('%Y-%m-%d')} at {tutor_scheduled_start.strftime('%Y-%m-%d %H:%M %Z')}."}, status=status.HTTP_400_BAD_REQUEST)
            '''
           if now < tutor_scheduled_start - timedelta(minutes=5):
             logger.error(f"Live-Class-Join-API = {session.tutor.user.email} Tried To Join Early ")
             return Response({"error": f"Live Class starts at {tutor_scheduled_start.strftime('%H:%M %Z')}"}, status=status.HTTP_400_BAD_REQUEST)
    
           if now > session.end_time.astimezone(pytz.timezone(tutor_timezone)):
             session.status = "FAILED"
             session.save()
             logger.error(f"Live-Class-Join-API = {session.tutor.user.email} Tried To Join After Class Ended ")
             return Response({"error": "Live Class time over"}, status=status.HTTP_400_BAD_REQUEST)


        elif user == session.learner:
    
           learner_timezone = get_timezone_by_country('Germany')
           now = timezone.now().astimezone(pytz.timezone(learner_timezone))
           learner_scheduled_start = session.scheduled_start_time.astimezone(pytz.timezone(learner_timezone))
           '''
           if session.date != now.date():
               logger.error(f"Live-Class-Join-API = {session.learner.email} Tried To Join On Wrong Date ")
               return Response({"error": f"This Live Class starts on {session.date.strftime('%Y-%m-%d')} at {tutor_scheduled_start.strftime('%Y-%m-%d %H:%M %Z')}."}, status=status.HTTP_400_BAD_REQUEST)
            
           if now < learner_scheduled_start - timedelta(minutes=5):
               logger.error(f"Live-Class-Join-API = {session.learner.email} Tried To Join Early ")
               return Response({"error": f"Live Class starts at {learner_scheduled_start.strftime('%H:%M %Z')}"}, status=status.HTTP_400_BAD_REQUEST)
           
           if now > session.end_time.astimezone(pytz.timezone(learner_timezone)):
               session.status = "FAILED"
               session.save()
               logger.error(f"Live-Class-Join-API = {session.learner.email} Tried To Join After Class Ended ")
               return Response({"error": "Live Class time over"}, status=status.HTTP_400_BAD_REQUEST)
            '''
        
        try:
            room_name = f"tutor-deemanths@iu.edu.in-session-{session.uid}"
            print(f"tutor-{session.tutor.user.email}")

            if session.status == 'SCHEDULED':
                create_livekit_room_sync(room_name)
                session.livekit_room_name = room_name
                session.primary_provider = 'LIVEKIT'
                session.status = "ONGOING"
                session.save()
                logger.info(f"Live-Class-Join-API = [Session {session.id}] LiveKit room created: {room_name}")
                print(f"Genrating Token for Live Class Session : {session.id}")
                generate_livekit_session_tokens(session_id=session.id)
                session.refresh_from_db()
            
        except Exception as e:
            session.status = "FAILED"
            session.save()
            logger.exception(f"Live-Class-Join-API = [Session {session.id}] LiveKit room creation failed.")
            
        fallback_url = None
        '''
        if settings.USE_DAILY_CO_FALLBACK and not session.daily_co_room_url:
            fallback_data = prepare_daily_co_fallback(session.id)
            session.daily_co_room_url = fallback_data['room_url']
            session.daily_co_tutor_url = fallback_data['tutor_url']
            session.daily_co_learner_url = fallback_data['learner_url']
            session.save()

            fallback_url=session.daily_co_room_url '''

        logger.info(f"Live-Class-Join-API = Response Sent Successfully")
        return Response({
            "session_id":session.id,
            "primary_provider": session.primary_provider,
            "livekit_cloud_url": settings.LIVEKIT_URL,
            "livekit_room_name": session.livekit_room_name,
            "role": url.role,
            "token": session.livekit_learner_token if url.role == 'learner' else session.livekit_tutor_token,
            "fallback_url" : fallback_url
            })
        
      except Exception as e:
            logger.error(f"Session Join initialization failed: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class LiveKitWebhookView(APIView):

    def verify_signature(self, request):
       
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            logger.error("LiveKit Webhook: Missing Authorization header")
            return Response({"error": "Missing Authorization header"}, status=status.HTTP_400_BAD_REQUEST)

        token = auth_header.replace("Bearer ", "").strip()
        try:
            decoded_token = jwt.decode(token, settings.LIVEKIT_API_SECRET, algorithms=["HS256"], options={"verify_nbf": False})
        except jwt.InvalidTokenError as e:
            logger.error(f"LiveKit Webhook: Invalid JWT token - {str(e)}")
            return Response({"error": "Invalid token"}, status=status.HTTP_403_FORBIDDEN)

        raw_body = request.body
        computed_hash = base64.b64encode(hashlib.sha256(raw_body).digest()).decode()
        token_hash = decoded_token.get('sha256')

        if not token_hash or not hmac.compare_digest(computed_hash, token_hash):
            logger.error("LiveKit Webhook: SHA256 signature mismatch")
            return Response({"error": "Signature mismatch"}, status=status.HTTP_403_FORBIDDEN)

        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as e:
            logger.error(f"LiveKit Webhook: Invalid JSON - {str(e)}")
            return Response({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)


    def post(self, request):
        event_or_response = self.verify_signature(request)
        if isinstance(event_or_response, Response):
           return event_or_response  # return error if verification failed

        try:
            event = json.loads(request.body)
            event_type = event['event']
            room_name = f"tutor-deemanths@iu.edu.in-session-2025-04-29-771cfd"
        
            try:
               session = LiveClassSession.objects.get(livekit_room_name=room_name)
            except LiveClassSession.DoesNotExist:
               logger.error(f"Livekit-Webhook-API = No session found for room: {room_name}. Event data: {event}")
               return Response({"error": f"Session not found for room: {room_name}"}, status=status.HTTP_404_NOT_FOUND)

       
            handler = getattr(self, f'handle_{event_type}', None)
            if handler:
               return handler(event, session, request)
            else:
               logger.error(f"Livekit-Webhook-API = Handler Not Found for event: {event_type}")
               return Response({"status": "Unhandled Event"}, status=status.HTTP_200_OK)

        except Exception as e:
           logger.error(f"Livekit-Webhook-API = Exception - {e} ")
           return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

    def handle_room_started(self, event, session, request):
        room = event['room']

        SessionEventLog.objects.create(
        session=session,
        event_type='room_started',
        metadata={
            'event_id': event['id'],
            'event_created_at': event['createdAt'],
            'room_name': room['name'],
            'room_sid': room['sid'],
            'created_at': room['creationTime'],
            'empty_timeout': room['emptyTimeout'],
            'turn_password': room['turnPassword'],  
            'enabled_codecs': room['enabledCodecs'],
            
        })
        return Response({"message": "Room Started"}, status=status.HTTP_200_OK)

    def handle_room_finished(self, event, session, request):
        room = event['room']

        SessionEventLog.objects.create(
        session=session,
        event_type='room_finished',
        metadata={
            'event_id': event['id'],
            'event_created_at': event['createdAt'],
            'room_name': room['name'],
            'room_sid': room['sid'],
            'created_at': room['creationTime'],
            'empty_timeout': room['emptyTimeout'],
            'turn_password': room['turnPassword'],  
            'enabled_codecs': room['enabledCodecs'],
            })
        
        return Response({"message": "Room Finished"}, status=status.HTTP_200_OK)
    
    def handle_participant_joined(self, event, session, request):
        participant = event['participant']
        room = event['room']

        SessionEventLog.objects.create(
            session=session,
            event_type='participant_joined',
            participant_sid=participant['sid'],
            participant_identity=participant['identity'],
            participant_role=self._extract_role(participant['identity']),
            metadata={
                'event_id': event['id'],
                'event_created_at': event['createdAt'],
                'empty_timeout': room['emptyTimeout'],
                'turn_password': room['turnPassword'],  
                'enabled_codecs': room['enabledCodecs'],
                
                'room': {
                   'name': room['name'],
                   'sid': room['sid'],
                   'num_participants': room.get('numParticipants'),
                   'num_publishers': room.get('numPublishers')
                },
                'participant': {
                    'sid': participant['sid'],
                    'identity': participant['identity'],
                    'state': participant['state'],
                    'joined_at': participant['joinedAt'],
                    'version': participant['version'],
                    'permission': participant['permission'],
                    'region': participant.get('region')
            }
                })
        
        return Response({"message": "Participant Joined"}, status=status.HTTP_200_OK)

    def handle_participant_left(self, event, session, request):
        participant = event['participant']
        room = event['room']

        SessionEventLog.objects.create(
            session=session,
            event_type='participant_left',
            participant_sid=participant['sid'],
            participant_identity=participant['identity'],
            participant_role=self._extract_role(participant['identity']),
            metadata={
                'event_id': event['id'],
                'event_created_at': event['createdAt'],
                'empty_timeout': room['emptyTimeout'],
                'turn_password': room['turnPassword'],  
                'enabled_codecs': room['enabledCodecs'],
                
                'room': {
                   'name': room['name'],
                   'sid': room['sid'],
                   'num_participants': room.get('numParticipants'),
                   'num_publishers': room.get('numPublishers')
                },
                'participant': {
                    'sid': participant['sid'],
                    'identity': participant['identity'],
                    'state': participant['state'],
                    'joined_at': participant['joinedAt'],
                    'version': participant['version'],
                    'permission': participant['permission'],
                    'region': participant.get('region')
            }})
        return Response({"message": "Participant Left"}, status=status.HTTP_200_OK)

    def handle_track_published(self, event, session, request):

            room = event['room']
            participant = event['participant']
            track = event['track']

            SessionEventLog.objects.create(
                session=session,
                event_type='track_published',
                participant_sid=event['participant']['sid'],
                participant_identity=event['participant']['identity'],
                participant_role=self._extract_role(event['participant']['identity']),
                metadata={
                    'event_id': event['id'],
                    'room': {
                        'name': room['name'],
                        'sid': room['sid']
                    },
                    'participant': {
                        'sid': participant['sid'],
                        'identity': participant['identity']
                    },
                    'track': {
                        'sid': track['sid'],
                        'type': track['type'],
                        'name': track.get('name'),
                        'source': track.get('source'),
                        'mime_type': track.get('mimeType'),
                        'mid': track.get('mid'),
                        'stream': track.get('stream'),
                        'layers': track.get('layers', []),
                        'codecs': track.get('codecs', [])
            }})
            return Response({"message": "Track Published"}, status=status.HTTP_200_OK)

    def handle_track_unpublished(self, event, session, request):
            room = event['room']
            participant = event['participant']
            track = event['track']

            SessionEventLog.objects.create(
                session=session,
                event_type='track_unpublished',
                participant_sid=event['participant']['sid'],
                participant_identity=event['participant']['identity'],
                metadata={
                    'event_id': event['id'],
                    'room': {
                        'name': room['name'],
                        'sid': room['sid']
                    },
                    'participant': {
                        'sid': participant['sid'],
                        'identity': participant['identity']
                    },
                    'track': {
                        'sid': track['sid'],
                        'type': track['type'],
                        'name': track.get('name'),
                        'source': track.get('source'),
                        'simulcast': track.get('simulcast'),
                        'mime_type': track.get('mimeType'),
                        'mid': track.get('mid'),
                        'stream': track.get('stream'),
                        'layers': track.get('layers', []),
                        'codecs': track.get('codecs', [])
            }})
            return Response({"message": "Track Unpublished"}, status=status.HTTP_200_OK)

    def handle_egress_started(self, event, session, request):
        egress_info = event.get('egressInfo', {})
        track_composite = egress_info.get('trackComposite', {})
        file = egress_info.get('file', {})
        file_results = egress_info.get('fileResults', [])

        SessionEventLog.objects.create(
        session=session,
        event_type='recording_started',
        metadata={
            'event_id': event['id'],
            'room': {
                'name': egress_info.get('roomName'),
                'sid': egress_info.get('roomId')
            },
            'egress': {
                'egress_id': egress_info.get('egressId'),
                'updated_at': egress_info.get('updatedAt'),
                'file': {
                    'filename': file.get('filename')
                },
                'track_composite': {
                    'audio_track_id': track_composite.get('audioTrackId'),
                    'video_track_id': track_composite.get('videoTrackId'),
                    'advanced': track_composite.get('advanced'),
                    'file_outputs': [
                        {
                            'filepath': output.get('filepath'),
                            's3': {
                                'region': output.get('s3', {}).get('region'),
                                'bucket': output.get('s3', {}).get('bucket')
                            }
                        }
                        for output in track_composite.get('fileOutputs', [])
                    ]
                },
                'file_results': file_results}})

        return Response({"message": "Recording Started"}, status=status.HTTP_200_OK)

    def handle_egress_ended(self, event, session,request):

        if event == "egress_ended":
            egress_info = request.data.get("egressInfo", {})
            egress_id = egress_info.get("egressId")

            try:
                recording = SessionRecording.objects.get(session=session, egress_id=egress_id)

                file_info = egress_info.get("file", {})
                file_size = int(file_info.get("size", 0))
                file_url = file_info.get("location") or file_info.get("filename") or file_info.get("filepath")

                recording.duration_seconds = int(file_info.get("duration", 0))
                recording.file_size_mb = round(file_size / (1024 * 1024), 2)
                recording.livekit_mp4_url = file_url
                recording.status = "COMPLETED"
                recording.save()

                SessionEventLog.objects.create(
                session=session,
                event_type="egress_ended",
                metadata={
                   "event_id": event["id"],
                   "egress_id": egress_id,
                   "status": egress_info.get("status"),
                   "file_url": file_url,
                   "duration_seconds": recording.duration_seconds,
                   "file_size_mb": recording.file_size_mb,
                })

                return Response({"message": "Session Recording Updated."}, status=status.HTTP_200_OK)

            except SessionRecording.DoesNotExist:
                return Response({"error": "Session Recording not found for this egress_id."}, status=404)

        return Response({"message": "Webhook received but not an egress_ended event."}, status=200)
    
    def _extract_role(self, identity):
        """Extracts 'tutor' or 'learner' from identity string"""
        return 'tutor' if identity.startswith('tutor-') else 'learner'



class StartLivekitRecordingAPIView(APIView):
    
    #permission_classes = [IsAuthenticated]

    def post(self, request):
        
        session_id = request.data.get("session_id")
        title = request.data.get("title", "Untitled Recording")
        room_name = request.data.get("room_name")
        video_track_id = request.data.get("video_track_id")
        audio_track_ids = request.data.get("audio_track_ids",[]) 
        
        if not session_id or not room_name or not video_track_id or not audio_track_ids:
            return Response({"error": "room_name, video_track_id, and audio_track_ids are required."},status=status.HTTP_400_BAD_REQUEST )
        
        try:
            session = LiveClassSession.objects.get(id=session_id)
        except LiveClassSession.DoesNotExist:
            return Response({f"Session With {session_id} Not Found "},status=status.HTTP_404_NOT_FOUND)
        
        
        safe_title = safe_title_for_recording(title=title,session_id=session_id)
        
        try:
            result = start_composite_egress(
            room_name=room_name,
            video_track_id=video_track_id,
            audio_track_ids=audio_track_ids,
            safe_title=safe_title)

            SessionRecording.objects.create(
                session=session,
                title=title,
                status="STARTED", 
            )
            
            return Response({
                "message": "Recording Started Successfully.",
                "egress_id": result.egress_id,
                "status": result.status,
                "room_name": room_name
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StopLivekitRecordingAPIView(APIView):
    
    #permission_classes = [IsAuthenticated]

    def post(self, request):
        egress_id = request.data.get("egress_id")
        session_id = request.data.get("session_id")

        if not egress_id or session_id:
            return Response({"error": "egress_id and session_id is required."},status=status.HTTP_400_BAD_REQUEST)
        
        try:
            session = LiveClassSession.objects.get(id=session_id)
        except LiveClassSession.DoesNotExist:
            return Response({f"Session With {session_id} Not Found "},status=status.HTTP_404_NOT_FOUND)
        
        try:
            result = stop_egress(egress_id=egress_id)
            session_recording = SessionRecording.objects.get(
                session=session,
                status="REQUESTED", )
            
            session_recording.egress_id = egress_id
            session_recording.save()
            
            return Response({
                "message": "Recording Stopped Successfully.",
                "egress_id": egress_id,
                "status": result.status
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetrieveRecordingsAPIView(APIView):
    
    #permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            #user = request.user
            learner_email = "deemz@iu.edu.in"
            user = User.objects.get(email=learner_email)
        except User.DoesNotExist:
            return Response({"error": "Learner Does Not Exist."},status=status.HTTP_404_NOT_FOUND)

        if not hasattr(user, 'learner'):
            return Response({"error": "Access Denied. This endpoint is for learners only."},status=status.HTTP_403_FORBIDDEN)

        try:
            recordings = SessionRecording.objects.filter(session__learner=user).order_by('-created_at')
            
            if not recordings.exists():
                return Response({"message": "You have no Recordings yet."},status=status.HTTP_200_OK)
            
            data = []
            for r in recordings:
                key = r.livekit_mp4_url
                signed_url = generate_r2_signed_url(key)
                data.append({
                    "id": r.id,
                    "title": r.title,
                    "recording_url": signed_url,
                    "recording_duration": r.duration_seconds,
                    "recording_file_size": r.file_size_mb,
                    "created_at": r.created_at.isoformat(),
                    "session_uid": r.session.uid,
                    "session_date": r.session.scheduled_start_time.isoformat()
                })

            return Response({"My Recordings": data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": "Something Went wrong while retrieving recordings.", "details": str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class LivekitTokenRefreshAPIView(APIView):
    
    #permission_classes = [IsAuthenticated]

    def post(self, request):
        
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({"error": "session_id required"},status=status.HTTP_400_BAD_REQUEST)

        try:
            session = LiveClassSession.objects.get(id=session_id,status__in=["ONGOING", "SCHEDULED"])

        except LiveClassSession.DoesNotExist:
            return Response({"error": "Invalid or inactive session"},status=status.HTTP_404_NOT_FOUND)

        user = request.user
        is_tutor = (user == session.tutor.user)
        is_learner = (user == session.learner)
        
        if not (is_tutor or is_learner):
            return Response({"error": "You are Not an Authorized participant"},status=status.HTTP_403_FORBIDDEN)
        
        if user ==session.tutor.user:
          generate_livekit_session_tokens(session_id=session_id,user=session.tutor.user)
          urls=generate_livekit_join_urls(session_id=session_id,user=session.tutor.user)
          return Response({"encoded_tutor_url": urls['encoded_tutor_url']},status=status.HTTP_200_OK)
        
        elif user ==session.learner:
          generate_livekit_session_tokens(session_id=session_id,user=session.learner)
          urls=generate_livekit_join_urls(session_id=session_id,user=session.learner)
          return Response({"encoded_learner_url": urls['encoded_learner_url']},status=status.HTTP_200_OK)
           

class StartRecordingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        
        session = get_object_or_404(LiveClassSession, id=session_id)
        if request.user != session.tutor.user:
            return Response({"error": "Only the Tutor Can Start Recordings"},status=status.HTTP_403_FORBIDDEN)

        if session.status != 'ONGOING': 
            return Response( {"error": "Recording Can only be started for Ongoing Sessions"}, status=status.HTTP_400_BAD_REQUEST)

        if hasattr(session, 'recording'):
            return Response({"error": "Recording already exists for this session"},status=status.HTTP_409_CONFLICT)

        try:
            egress_id = start_livekit_recording(session)
            return Response({"status": "Recording Started","egress_id": egress_id}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)},status=status.HTTP_503_SERVICE_UNAVAILABLE )



class QoSTelemetryAPIView(APIView):
    def post(self, request):

        session_id = request.data['session_id']
        try:
            session = get_object_or_404(LiveClassSession,pk=session_id)
        
            conditions = {
                'high_packet_loss': float(request.data['packet_loss']) > 0.2,
                'high_latency': int(request.data['latency']) > 500,
                'low_bitrate': int(request.data['bitrate']) < 500}

            failed_conditions = [name for name, is_true in conditions.items() if is_true]
            needs_fallback = len(failed_conditions) >= 2  # At least 2 conditions true

            if needs_fallback and not session.is_fallback_triggered:
                reason_mapping = {
                   'high_packet_loss': 'packet loss > 20%',
                   'high_latency': 'latency > 500ms',
                   'low_bitrate': 'bitrate < 500kbps'}
                
                reasons = [reason_mapping[cond] for cond in failed_conditions]
            
                return Response({
                    "action": "Continue With fallback",
                    "reason": f"Poor Connection Due to: {', '.join(reasons)}",
                    "metrics": {
                        "packet_loss": request.data['packet_loss'],
                        "latency": request.data['latency'],
                        "bitrate": request.data['bitrate']
                    }}, status=status.HTTP_200_OK)
                
            return Response({"action":"Continue Without Fallback"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)    



class DailyCoWebhookView(APIView):

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # Signature Validation
        signature = request.headers.get('Daily-Signature')
        computed_sig = hmac.new(
            settings.DAILY_CO_WEBHOOK_SECRET.encode(),
            request.body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, computed_sig):
            logger.warning("Invalid Daily.co webhook signature")
            return Response({"status": "Invalid signature"}, status=403)

        # Process Events
        try:
            data = json.loads(request.body)
            event_type = data.get('type')

            if event_type == "room.occupied":
                self._handle_room_occupied(data['payload']['room'])
            elif event_type == "recording.completed":
                self._handle_recording(data['payload'])

            return Response({"status": "processed"})

        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            return Response(
                {"error": "Bad webhook data"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    def _handle_room_occupied(self, room_name):
        """Mark session as active when first participant joins"""
        try:
            session_id = int(room_name.split("-")[-1])
            LiveClassSession.objects.filter(
                pk=session_id,
                daily_co_room=room_name,
                status="SCHEDULED"
            ).update(status="ONGOING")
        except (ValueError, IndexError):
            logger.warning(f"Invalid room name format: {room_name}")

    def _handle_recording(self, payload):
        """Save recording metadata"""
        try:
            session = LiveClassSession.objects.get(
                daily_co_room=payload['room']
            )
            session.recording_url = payload['recording']['url']
            session.save()
        except LiveClassSession.DoesNotExist:
            logger.warning(f"Recording for unknown room: {payload['room']}")

class SessionTelemetryAPIView(APIView):
   # permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(LiveClassSession, pk=session_id)
        
        SessionTelemetry.objects.create(
            session=session,
            user=request.user,
            packet_loss=request.data.get('packet_loss'),
            jitter_ms=request.data.get('jitter'),
            bitrate_kbps=request.data.get('bitrate')
        )

        # Auto-trigger fallback if QoS is poor
        if request.data.get('packet_loss') > 0.2:  # 20% packet loss
            trigger_fallback_if_available(session.id)

        return Response({"status": "recorded"})

def trigger_fallback_if_available(session_id):
    session = LiveClassSession.objects.get(pk=session_id)
    if session.daily_co_room and not session.fallback_triggered:
        session.primary_provider = "DAILY"
        session.fallback_triggered = True
        session.fallback_reason=''
        session.save()
        
        # Notify both participants
        notify_participants.delay(
            session.id,
            "Switched to backup connection due to poor quality",
            "provider_switch"
        )

class SessionControlAPIView(APIView):
    
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        # Get and validate session
        session = get_object_or_404(LiveClassSession, pk=session_id)

        # Permission Check: Only tutor or admin can control
        if not (request.user == session.tutor.user or request.user.is_staff):
            return Response(
                {"error": "Only tutor can control session"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # Action Validation
        action = request.data.get('action')
        if action not in ['mute', 'end', 'record']:
            return Response(
                {"error": "Invalid action"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle Actions
        if action == "mute":
            return self._handle_mute(session, request.data)
        elif action == "end":
            return self._handle_end(session)
        elif action == "record":
            return self._handle_recording(session)

    def _handle_mute(self, session, data):
        """Mute participant via Agora REST API"""
        try:
            user_id = data.get('user_id')
            if not user_id:
                return Response(
                    {"error": "Missing user_id"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Only allow muting the student
            if user_id != session.learner.id:
                return Response(
                    {"error": "Can only mute student"}, 
                    status=status.HTTP_403_FORBIDDEN
                )

            return Response(
                {"error": "Mute operation failed"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except Exception as e:
            logger.error(f"Mute failed: {str(e)}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _handle_end(self, session):
        """End session prematurely"""
        session.end_time = timezone.now()
        session.status = "COMPLETED"
        session.save()

        # Clean up Daily.co room if exists
        if session.daily_co_room:
            DailyCoService().delete_room(session.daily_co_room)

        return Response({"status": "session_ended"})