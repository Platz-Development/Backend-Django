from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
from .models import LiveClassSession
from .services.daily_co_service import DailyCoService
import requests
from django.core.files import File
from io import BytesIO
from .models import SessionRecording

logger = logging.getLogger(__name__)


#@shared_task(bind=True, max_retries=3)
def download_recording(self, recording_id):
    recording = SessionRecording.objects.get(id=recording_id)
    
    try:
        # 1. Download from LiveKit
        response = requests.get(recording.livekit_mp4_url,stream=True,timeout=30)
        response.raise_for_status()
        
        # 2. Save locally
        file_name = f"session_{recording.session.id}.mp4"
        recording.local_video_file.save(file_name,File(BytesIO(response.content)),save=True)
        
        # 3. Update status
        recording.status = 'COMPLETED'
        recording.file_size_mb = recording.local_video_file.size / (1024 * 1024)
        recording.save()
        
    except Exception as e:
        recording.download_attempts += 1
        recording.save()
        # raise self.retry(exc=e, countdown=60 * recording.download_attempts)


@shared_task
def notify_participants(session_id, message, event_type="notification"):
    """
    Notifies both tutor and student about session events
    Types: notification, fallback, ending_soon
    """
    try:
        session = LiveClassSession.objects.select_related('tutor__user', 'user').get(pk=session_id)
        
        # In production, integrate with your notification system (Email/WS/Push)
        logger.info(f"Notifying session {session_id}: {message}")
        
        # Example: WebSocket notification
        participants = [session.tutor.user, session.learner]
        for user in participants:
            send_websocket_notification.delay(
                user_id=user.id,
                message={
                    "type": event_type,
                    "session_id": session_id,
                    "content": message,
                    "timestamp": timezone.now().isoformat()
                }
            )

    except Exception as e:
        logger.error(f"Notification failed for session {session_id}: {str(e)}")

@shared_task(bind=True, max_retries=2)
def send_websocket_notification(self, user_id, message):
    """
    Sends actual WebSocket message (mock implementation)
    In production, integrate with Channels or similar
    """
    try:
        # Replace with actual WebSocket implementation
        logger.info(f"WS to user {user_id}: {message}")
    except Exception as e:
        logger.warning(f"WS failed to user {user_id}, retrying...")
        raise self.retry(exc=e)

@shared_task
def cleanup_expired_sessions():
    """
    Scheduled task to end expired sessions and clean resources
    Runs every 5 minutes via Celery beat
    """
    try:
        now = timezone.now()
        expired_sessions = LiveClassSession.objects.filter(
            end_time__lte=now,
            status="ONGOING"
        )

        for session in expired_sessions:
            # End session
            session.status = "COMPLETED"
            session.save()

            # Clean Daily.co room if exists
            if session.daily_co_room:
                DailyCoService().delete_room(session.daily_co_room)

            # Notify participants
            notify_participants.delay(
                session.id,
                "Session has ended automatically",
                "session_ended"
            )

        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    except Exception as e:
        logger.error(f"Session cleanup failed: {str(e)}")

@shared_task(bind=True, max_retries=3)
def process_session_recording(self, session_id, recording_url):
    """
    Handles post-recording processing:
    - Storage to S3/Cloud
    - Transcription
    - Thumbnail generation
    """
    try:
        session = LiveClassSession.objects.get(pk=session_id)
        
        # 1. Download recording (mock implementation)
        recording_data = requests.get(recording_url, timeout=10).content
        
        # 2. Store in permanent storage
        storage_path = f"recordings/session_{session_id}/{timezone.now().date()}.mp4"
        store_recording_in_cloud(storage_path, recording_data)
        
        # 3. Update session
        session.recording_url = storage_path
        session.save()
        
        logger.info(f"Processed recording for session {session_id}")

    except requests.exceptions.RequestException as e:
        logger.warning(f"Recording download failed, retrying...")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Recording processing failed: {str(e)}")
        raise

# Helper functions
def store_recording_in_cloud(path, data):
    """Mock function - replace with actual cloud storage integration"""
    logger.info(f"Storing recording at {path} (size: {len(data)} bytes)")
    # Example for AWS S3:
    # import boto3
    # s3 = boto3.client('s3')
    # s3.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=path, Body=data)