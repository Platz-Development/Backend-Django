import requests
from django.conf import settings
from django.urls import reverse
from datetime import datetime, timedelta
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import requests
from django.conf import settings
from datetime import datetime, timedelta
import jwt
from django.shortcuts import get_object_or_404
from live_class_streaming.models import LiveClassSession
from get_timezone import get_timezone_by_country
import pytz



logger = logging.getLogger(__name__)


def prepare_daily_co_fallback(session_id):

    session = get_object_or_404(LiveClassSession,pk=session_id)
    
    learner=session.learner
    learner_country =learner.country
    learner_timezone = get_timezone_by_country(learner_country)
    learner_end_time = session.end_time.astimezone(pytz.timezone(learner_timezone))
    expires_at_learner = learner_end_time + timedelta(minutes=10)

    tutor=session.tutor.user
    tutor_country =tutor.country
    tutor_timezone = get_timezone_by_country(tutor_country)
    tutor_end_time = session.end_time.astimezone(pytz.timezone(tutor_timezone))
    expires_at_tutor = tutor_end_time + timedelta(minutes=10)

    room_res = requests.post(
        "https://api.daily.co/v1/rooms",
        headers={"Authorization": f"Bearer {settings.DAILY_API_KEY}"},
        json={
            "name": f"tutor-{session.tutor.id}-{session.uid[:8]}",
            "privacy":"private",
            "properties": {
                "max_participants": 2,
                "enable_chat": True,
                "enable_screenshare": True,
                "enable_recording": True,
                "start_video_off": True,
                "start_audio_off": True,
                "enable_network_ui": True,  
                "exp": int((session.end_time + timedelta(minutes=30)).timestamp()), 
                }})
    
    room_res.raise_for_status()
    room_data = room_res.json()

    tutor_token = generate_daily_token(
        room_name=room_data['name'],
        user_id=f"tutor-{session.tutor.id}",
        is_admin=True,
        expires_at=expires_at_tutor)
    
    session.daily_co_tutor_token = tutor_token

    learner_token = generate_daily_token(
        room_name=room_data['name'],
        user_id=f"learner-{session.learner.id}",
        is_admin=False,
        expires_at=expires_at_learner)
    
    session.daily_co_learner_token = learner_token
    
    session.daily_co_room_name = room_data['name']
    session.daily_co_room_url = room_data['url']
    session.save()

    return {
        "room_url": room_data['url'],
        "tutor_url": f"{room_data['url']}?t={tutor_token}",
        "learner_url": f"{room_data['url']}?t={learner_token}",
        "expires_at": expires_at_tutor
    }

def generate_daily_token(room_name, user_id, is_admin, expires_at):
    """
    Generates JWT for Daily.co with role-based permissions
    """
    payload = {
        "aud": "daily",
        "iss": settings.DAILY_API_KEY,
        "sub": settings.DAILY_DOMAIN,
        "room": room_name,
        "user_id": user_id,
        "exp": int(expires_at.timestamp()),
        "is_owner": is_admin,
        "permissions": {
            "can_send": True,
            "can_admin": is_admin,
            "can_screenshare": True,  # Only tutor can share
            "can_evict": is_admin        # Only tutor can remove
        }
    }
    return jwt.encode(payload, settings.DAILY_API_SECRET, algorithm="HS256")


class DailyCoService:
    
    def __init__(self):
        self.base_url = "https://api.daily.co/v1"
        self.headers = {
            "Authorization": f"Bearer {settings.DAILY_CO_API_KEY}",
            "Content-Type": "application/json"
        }

    def get_room_participants(self, room_name):
        """Verify active participants in a room"""
        try:
            response = requests.get(
                f"{self.base_url}/rooms/{room_name}",
                headers=self.headers,
                timeout=3
            )
            return response.json().get("participant_count", 0)
        except requests.exceptions.RequestException:
            return 0

    def delete_room(self, room_name):
        """Forcefully cleanup a room"""
        try:
            requests.delete(
                f"{self.base_url}/rooms/{room_name}",
                headers=self.headers,
                timeout=3
            )
            return True
        except requests.exceptions.RequestException:
            return False

    def _get_webhook_url(self):
        """Generate absolute URL for webhooks"""
        return (
            f"{settings.BASE_URL}"
            f"{reverse('daily-co-webhook')}"
        )
