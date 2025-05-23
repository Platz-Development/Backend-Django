import re
import uuid

def safe_title_for_recording(title, session_id):
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title).strip('_')
    return f"recordings/{safe_title}-{session_id}"
