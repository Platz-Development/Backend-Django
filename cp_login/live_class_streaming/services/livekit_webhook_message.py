from livekit.api import LiveKitAPI
from django.conf import settings
from django.utils import timezone
import logging
import asyncio
from rest_framework.response import Response



LIVEKIT_API_KEY = "APIgaGhNfsBshoX"  
LIVEKIT_API_SECRET = "AHDvf9YF8rDob8v6fJ23D5UAefZT62xR5phWSFPZKgyC" 
LIVEKIT_URL = "https://campusplatz-ckqf7pkr.livekit.cloud"


logger = logging.getLogger(__name__)

#5129320108051886
async def create_livekit_client(room_name: str, max_retries: int = 5):
    attempt = 0
    delay = 2  # initial retry delay in seconds

    while attempt < max_retries:
        try:
            lkapi = LiveKitAPI(
                url=LIVEKIT_URL,
                api_key=LIVEKIT_API_KEY,
                api_secret=LIVEKIT_API_SECRET
            )
            logger.info(f"LiveKitAPI client initialized successfully for room: {room_name}")
            return lkapi
        except Exception as e:
            logger.warning(f"[Attempt {attempt + 1}] Failed to initialize LiveKitAPI: {e}")
            await asyncio.sleep(delay)
            attempt += 1
            delay *= 2  # exponential backoff

    logger.error(f"Failed to initialize LiveKitAPI after {max_retries} attempts for room: {room_name}")
    raise ConnectionError("Could not initialize LiveKitAPI after retries.")


def notify_livekit_room(room_name: str, message: str):
    """Sends a message to all participants in the specified room."""
    try:
        client = create_livekit_client()
        client.send_data(
            room=room_name,
            data=message.encode("utf-8"),
            kind="RELIABLE"
        )
        logger.info(f"Message sent to room {room_name}: {message}")
    except Exception as e:
        logger.error(f"Failed to send message to room {room_name}: {e}")



def send_livekit_webhook_message(event):
    
    room = event.get("room", {})
    room_name = room.get("name")
    event = event.get("event")

    if event == "egress_started":
        message = f"Recording Has Started in Room '{room_name}'."
        notify_livekit_room(room_name, message)

    elif event == "egress_ended":
        egress_info = event.get("egressInfo", {})
        file_url = egress_info.get("file", {}).get("location")
        if file_url:
            message = f"Recording Has Ended. File Available At: {file_url}"
        else:
            message = "Recording Has Ended."

    elif event["event"] == "track_published":
        track_info = event.get("track", {})
        track_name = track_info.get("name", "Unknown Track")
        track_type = track_info.get("type", "Unknown Type")
        participant_id = event.get("participant", {}).get("identity", "Unknown Participant")
        message = f"Track '{track_name}' of type '{track_type}' has been published by {participant_id}."
        notify_livekit_room(room_name, message)

    elif event["event"] == "track_unpublished":
        track_info = event.get("track", {})
        track_name = track_info.get("name", "Unknown Track")
        participant_id = event.get("participant", {}).get("identity", "Unknown Participant")
        message = f"Track '{track_name}' has been unpublished by {participant_id}."
        notify_livekit_room(room_name, message)

    elif event["event"] == "participant_joined":
        participant = event.get("participant", {})
        participant_name = participant.get("identity", "Unknown Participant")
        message = f"{participant_name} has joined the room."
        notify_livekit_room(room_name, message)

    elif event["event"] == "participant_left":
        participant = event.get("participant", {})
        participant_name = participant.get("identity", "Unknown Participant")
        message = f"{participant_name} has left the room."
        notify_livekit_room(room_name, message)

    elif event["event"] == "room_started":
        message = f"Room '{room_name}' has started."
        notify_livekit_room(room_name, message)

    elif event["event"] == "room_ended":
        message = f"Room '{room_name}' has ended."
        notify_livekit_room(room_name, message)

    elif event["event"] == "ingress_started":
        message = f"Ingress has started in Room '{room_name}'."
        notify_livekit_room(room_name, message)

    elif event["event"] == "ingress_ended":
        message = f"Ingress has ended in Room '{room_name}'."
        notify_livekit_room(room_name, message)

    return Response({"message": "Webhook Event Processed."}, status=200)