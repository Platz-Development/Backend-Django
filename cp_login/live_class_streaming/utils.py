import re
import uuid

def format_recording_path(title, session_id):
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title).strip('_')
    return f"recordings/{safe_title}-{session_id}.mp4"
