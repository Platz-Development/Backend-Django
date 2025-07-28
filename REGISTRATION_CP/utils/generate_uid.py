import hashlib
import uuid

#=================================================== Generate Uid For User Function ==============================================================================

def generate_uid_for_user(model_class, field_name="uid", suffix_length=8, max_attempts=100):
    
    for _ in range(max_attempts):
        short_hash = hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:suffix_length]
        uid = f"{short_hash}"
        if not model_class.objects.filter(**{field_name: uid}).exists():
            return uid
    raise ValueError(
        f"Could Not Generate a Unique UID for {model_class.__name__}.{field_name} After {max_attempts} attempts."
    )
