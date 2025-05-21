import asyncio
import aiohttp
from livekit import api
from livekit.protocol import egress
from django.conf import settings


LIVEKIT_API_KEY = "APIgaGhNfsBshoX"  
LIVEKIT_API_SECRET = "AHDvf9YF8rDob8v6fJ23D5UAefZT62xR5phWSFPZKgyC" 
LIVEKIT_URL = "https://campusplatz-ckqf7pkr.livekit.cloud"

def start_composite_egress(room_name, video_track_id, audio_track_ids):
    """
    Start recording with learner's video and both tutor + learner audio tracks.
    """
    async def _start():
        async with aiohttp.ClientSession() as session:
            lkapi = api.LiveKitAPI(session, LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            
            advanced_encoding = egress.EncodingOptions(
                width=640,
                height=360,
                video_bitrate=500,                         # 1000 kbps is good for 360p
                key_frame_interval=4   )

            request = egress.TrackCompositeEgressRequest(
                room_name=room_name,
                video_track_id=video_track_id,
                audio_track_ids=audio_track_ids,

                file_outputs=egress.EncodedFileOutput(
                    file_type=egress.EncodedFileType.MP4,
                    filepath=f"recordings/{room_name}.mp4",
                    s3=egress.S3Upload(
                        access_key="c5b0c094a3ad8581e00746d8d7f36873",
                        secret="03f7a1c3c586775385f82b966f785b0e87c2d024110bee4320b19f251ca68710",
                        region="auto",
                        bucket="livekit-recordings",
                        endpoint="https://25f23cf5d85b78cabf8706e7fa7e6c55.r2.cloudflarestorage.com",  # required for non-AWS
                        force_path_style=True )),
                
                advanced=advanced_encoding,
                #preset=egress.EncodingOptionsPreset.H264_720P_30, # OR use advanced options: # advanced=egress.EncodingOptions(bitrate=2000, resolution="720p")
            )
            return await lkapi.egress.start_track_composite_egress(request)

    return asyncio.run(_start())

def stop_egress(egress_id):
    """
    Stop a currently running egress by ID.
    """
    async def _stop():
        async with aiohttp.ClientSession() as session:
            lkapi = api.LiveKitAPI(session, LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            return await lkapi.egress.stop_egress(
                egress.StopEgressRequest(egress_id=egress_id)
            )

    return asyncio.run(_stop())
