
from datetime import datetime, timedelta
from django.conf import settings
from livekit.api import AccessToken, VideoGrants
import urllib.parse
from django.urls import reverse
from get_timezone import get_timezone_by_country
import pytz
from live_class_streaming.models import LiveClassSession
from django.shortcuts import get_object_or_404
import requests
from django.conf import settings
from rest_framework.exceptions import APIException
import logging
from livekit.api import LiveKitAPI,CreateRoomRequest,ListRoomsRequest
import asyncio
from django.utils import timezone
import secrets
import hmac,hashlib
from urllib.parse import quote
from live_class_streaming.models import LiveKitClassJoinURL



LIVEKIT_API_KEY = "APIgaGhNfsBshoX"  
LIVEKIT_API_SECRET = "AHDvf9YF8rDob8v6fJ23D5UAefZT62xR5phWSFPZKgyC" 
LIVEKIT_URL = "https://campusplatz-ckqf7pkr.livekit.cloud"

logger = logging.getLogger(__name__)

def create_livekit_room_sync(room_name, max_retries=5):
    async def _create():
        attempt = 0
        while attempt < max_retries:
            try:
                async with LiveKitAPI(
                    url=LIVEKIT_URL,
                    api_key=LIVEKIT_API_KEY,
                    api_secret=LIVEKIT_API_SECRET
                ) as lkapi:
        
                    rooms_response = await lkapi.room.list_rooms(list=ListRoomsRequest())

                    if any(room.name == room_name for room in rooms_response.rooms):
                        logger.info(f"LiveKit Room '{room_name}' already exists. Skipping creation.")
                        return True

                    await lkapi.room.create_room(CreateRoomRequest(
                        name=room_name,
                        empty_timeout=900,
                        max_participants=2
                    ))
                    logger.info(f"LiveKit Room '{room_name}' created successfully.")
                    return True
            except Exception as e:
                attempt += 1
                logger.error(f"Attempt {attempt} to create LiveKit Room '{room_name}' failed: {e}")
                await asyncio.sleep(1)

        logger.critical(f"Failed to create LiveKit Room '{room_name}' after {max_retries} attempts.")
        return False

    return asyncio.run(_create())

#============================ Generate LiveKit Tokens  =========================================

def generate_livekit_session_tokens(session_id,user=None):
    
    session = get_object_or_404(LiveClassSession, pk=session_id)
    
    if not session.livekit_room_name:
        session.livekit_room_name = f"tutor-{session.tutor.user.email}-session-{session.uid}"


    GERMANY_TZ = pytz.timezone("Europe/Berlin")
    BUFFER_MINUTES = 10  
    
    if isinstance(session.end_time, (int, float)):
        session_end_dt = datetime.fromtimestamp(session.end_time, tz=pytz.UTC)
    else:
        session_end_dt = session.end_time

    end_time_berlin = session_end_dt.astimezone(GERMANY_TZ)
    expires_at = end_time_berlin + timedelta(minutes=BUFFER_MINUTES)
    ttl = int(expires_at.timestamp()) - int(timezone.now().timestamp())
    

    try:
        if user:
            if user == session.tutor.user:
                token = AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
                token.with_identity(f"tutor-{session.tutor.user.email}")
                token.with_ttl(timedelta(seconds=ttl))
                token.with_grants(VideoGrants(
                    room=session.livekit_room_name,
                    room_join=True,
                    room_record=True,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                ))
                session.livekit_tutor_token = token.to_jwt()
                
            elif user == session.learner:
                token = AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
                token.with_identity(f"learner-{session.learner.email}")
                token.with_ttl(timedelta(seconds=ttl))
                token.with_grants(VideoGrants(
                    room=session.livekit_room_name,
                    room_join=True,
                    room_record=True,
                    can_publish=True,
                    can_subscribe=True,
                ))
                session.livekit_learner_token = token.to_jwt()
                
        else:
            tutor_token = AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
            tutor_token.with_identity(f"tutor-{session.tutor.user.email}")
            tutor_token.with_ttl(timedelta(seconds=ttl))
            tutor_token.with_grants(VideoGrants(
                room=session.livekit_room_name,
                room_join=True,
                room_record=True,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            ))

            learner_token = AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
            learner_token.with_identity(f"learner-{session.learner.email}")
            learner_token.with_ttl(timedelta(seconds=5000))
            learner_token.with_grants(VideoGrants(
                room=session.livekit_room_name,
                room_join=True,
                room_record=True,
                can_publish=True,
                can_subscribe=True,
            ))

            session.livekit_tutor_token = tutor_token.to_jwt()
            session.livekit_learner_token = learner_token.to_jwt()
            
        session.save()
        logger.info("LiveKit tokens generated and saved.")
        return session.livekit_tutor_token, session.livekit_learner_token

    except Exception as e:
        logger.error(f"LiveKit token generation failed: {str(e)}")
        return None


#============================ Generate LiveKit Join URLs  =========================================


MAX_RETRIES = 5
KEY_LENGTH = 10
GERMANY_TZ = pytz.timezone("Europe/Berlin")
BUFFER_MINUTES = 10  
base_url = f'{settings.FRONTEND_URL}livekit/join-live-class/'


def generate_short_key(length=KEY_LENGTH):
    return secrets.token_urlsafe(length)[:length]


def get_unique_key():
    for _ in range(MAX_RETRIES):
        key = generate_short_key()
        if not LiveKitClassJoinURL.objects.filter(key=key).exists():
            return key
    return generate_short_key()


def generate_signed_url(key, expires_at):

    expires_at_str = expires_at.isoformat()
    safe_expires_at_str = quote(expires_at_str, safe='')
    data = f"{key}{expires_at_str}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(), data.encode(), hashlib.sha256
    ).hexdigest()
    
    return f"{base_url}?key={key}&expires_at={safe_expires_at_str}&signature={signature}"


def generate_livekit_join_urls(session_id, user=None):
    
    session = get_object_or_404(LiveClassSession, pk=session_id)

    if isinstance(session.end_time, (int, float)):
        session_end_dt = datetime.fromtimestamp(session.end_time, tz=pytz.UTC)
    else:
        session_end_dt = session.end_time

    end_time_berlin = session_end_dt.astimezone(GERMANY_TZ)
    expires_at = end_time_berlin + timedelta(minutes=BUFFER_MINUTES)

    try:
        if user:
            if user == session.tutor.user:
                tutor_key = get_unique_key()  

                LiveKitClassJoinURL.objects.create(
                key=tutor_key,
                session=session,
                role='tutor',
                expires_at=expires_at
            )
                tutor_url = generate_signed_url(tutor_key, expires_at)

                session.livekit_tutor_url = tutor_url
                session.save()
                return {"tutor_url": tutor_url }

            elif user == session.learner:
                learner_key = get_unique_key()  

                LiveKitClassJoinURL.objects.create(
                key=learner_key,
                session=session,
                role='learner',
                expires_at=expires_at
            )
                learner_url = generate_signed_url(learner_key, expires_at)

                session.livekit_learner_url = learner_url
                session.save()
                return {"learner_url": learner_url }
            
        else:
            tutor_key = get_unique_key()  

            LiveKitClassJoinURL.objects.create(
                key=tutor_key,
                session=session,
                role='tutor',
                expires_at=expires_at
            )
            tutor_url = generate_signed_url(tutor_key, expires_at)
            
            learner_key = get_unique_key()  

            LiveKitClassJoinURL.objects.create(
                key=learner_key,
                session=session,
                role='learner',
                expires_at=expires_at
            )
            learner_url = generate_signed_url(learner_key, expires_at)

            session.livekit_tutor_url = tutor_url
            session.livekit_learner_url = learner_url
            session.save()
            return {
            "tutor_url": tutor_url,
            "learner_url": learner_url }

    except Exception as e:
        logger.error(f"Error generating join URLs for session {session_id}: {str(e)}")
        return {}


logger = logging.getLogger(__name__)

class RecordingServiceException(APIException):
    status_code = 503
    default_detail = 'Recording service unavailable'
    default_code = 'service_unavailable'

def validate_recording_prerequisites(session):
    """Check LiveKit room exists"""
    # Verify room exists
    room_info = requests.get(
        f"{settings.LIVEKIT_API_HOST}/twirp/livekit.RoomService/ListRooms",
        auth=(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    ).json()
    if session.livekit_room_name not in [r['name'] for r in room_info['rooms']]:
        raise RecordingServiceException("Room not active on LiveKit")


def start_livekit_recording(session):
  
    try:
        
        validate_recording_prerequisites(session)
        payload = {
            "room_name": session.livekit_room_name,
            "output": {
                "file_type": "MP4",
                "filepath": f"tutor-{session.tutor.id}/session_{session.id}.mp4",
            },
            "options": {
                "preset": "1080p",
                "video_codec": "H264",
                "participant": {
                    "identity": f"learner-{session.learner.id}",
                    "video": True,
                    "audio": True  # Learner audio
                },
                "additional_audio": [
                    f"tutor-{session.tutor.id}"  # Include tutor audio
                ]
            }
        }

        # 2. Send request to LiveKit
        response = requests.post(
            f"{settings.LIVEKIT_API_HOST}/twirp/livekit.Egress/StartRoomCompositeEgress",
            json=payload,
            auth=(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET),
            timeout=10
        )

        # 3. Handle response
        if response.status_code == 200:
            data = response.json()
            return data['egress_id']
        else:
            logger.error(f"LiveKit Recording API error: {response.text}")
            raise RecordingServiceException(detail=response.text)

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error Starting Recording: {str(e)}")
        raise RecordingServiceException(detail=str(e))