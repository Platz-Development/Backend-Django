import os
from django.core.exceptions import ValidationError
from django.conf import settings
from PIL import Image
from io import BytesIO
from rest_framework import serializers
from django.core.signing import TimestampSigner
from django.urls import reverse
import mimetypes
import re
import hashlib
from moviepy import VideoFileClip
import ffmpeg
from rest_framework.exceptions import ValidationError
import base64
import six
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers


    
#============================= Image Validation Code ======================================


class SecureFileValidator:
   
   
    ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.pdf']
    ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'application/pdf']
    MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB
    MIN_IMAGE_DIMENSIONS = (100, 100)  # 100x100px minimum
    BLOCKED_EXTENSIONS = ['.exe', '.js', '.jar', '.php', '.sh']
    
    def __init__(self, allowed_extensions=None,field_name=None, allowed_mime_types=None, max_size=None):
        self.allowed_extensions = allowed_extensions or ['.jpg', '.jpeg', '.png', '.pdf']
        self.allowed_mime_types = allowed_mime_types or [ 'image/jpeg', 'image/png',  'application/pdf']
        self.max_size = max_size if max_size is not None else 3 * 1024 * 1024 
        self.field_name = field_name 
        
        try:
            import magic
            self.mime = magic.Magic(mime=True)
        except (ImportError, AttributeError):
            self.mime = None
    
    def __call__(self, value):
        """Main validation pipeline"""
        self.validate_extension(value)
        self.validate_blocked_types(value)
        self.validate_file_size(value)
        
        if self.mime:
            self.validate_mime_type(value)
        
        if self._is_image(value.name):
            self.validate_image_content(value)
        elif value.name.lower().endswith('.pdf'):
            self.validate_pdf_header(value)


    def validate_file_size(self, value):
     
     if self.max_size is None:
        raise ValidationError( f"{self.field_name or 'File'} size validation is not configured")
     if not isinstance(self.max_size, (int, float)):
        raise ValidationError( f"{self.field_name or 'File'} size limit configuration")
     if value.size > self.max_size:
        raise ValidationError(
            f"{self.field_name or 'File'} size too large. Max size: {self.max_size/1024/1024}MB"
        )


    def _is_image(self, filename):
        return filename.lower().endswith(('.jpg', '.jpeg', '.png'))

    def validate_extension(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(
                 f"{self.field_name or 'File'} Invalid file extension. Allowed: {', '.join(self.allowed_extensions)}"
            )

    def validate_blocked_types(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext in self.BLOCKED_EXTENSIONS:
            raise ValidationError( f"{self.field_name or 'File'} Potentially dangerous file type blocked")

    
    def validate_mime_type(self, value):
        file_start = value.read(2048)
        value.seek(0)
        mime_type = self.mime.from_buffer(file_start)
        if mime_type not in self.allowed_mime_types:
            raise ValidationError(
                 f"{self.field_name or 'File'} Invalid file content. Detected MIME: {mime_type}" )

    def validate_image_content(self, value):
        try:
            with Image.open(value) as img:
                img.verify()
                
                img = Image.open(value)  # Reopen after verify
                if img.width < self.MIN_IMAGE_DIMENSIONS[0] or \
                   img.height < self.MIN_IMAGE_DIMENSIONS[1]:
                    raise ValidationError(
                         f"{self.field_name or 'File'} Image too small. Minimum {self.MIN_IMAGE_DIMENSIONS[0]}x{self.MIN_IMAGE_DIMENSIONS[1]}px required" )
                
                # Strip EXIF data
                data = list(img.getdata())
                clean_img = Image.new(img.mode, img.size)
                clean_img.putdata(data)
                
                # Save cleaned image back to memory
                output = BytesIO()
                clean_img.save(output, format=img.format)
                value.file = output  # Replace original file
                
        except Exception as e:
            raise ValidationError( f"{self.field_name or 'File'} Invalid image: {str(e)}")

    def validate_pdf_header(self, value):
        header = value.read(4)
        value.seek(0)
        if header != b'%PDF':
            raise ValidationError (f"{self.field_name or 'File'} Invalid PDF file")
        



class SecureFileField(serializers.FileField):
    """
    End-to-end secure file field with:
    - Validation
    - Secure URL generation
    - Anti-tampering protection
    """
    
    def __init__(self, **kwargs):

        self.field_display_name = kwargs.pop('field_name', None)
        validator_config = {
            'field_name':self.field_display_name,
            'allowed_extensions': kwargs.pop('allowed_extensions', None),
            'allowed_mime_types': kwargs.pop('allowed_mime_types', None),
            'max_size': kwargs.pop('max_size', None)
        }
        self.validator = SecureFileValidator(**validator_config)
        
        super().__init__(**kwargs)
        self.validators.append(self.validator)

    def to_representation(self, value):
        """Generate secure URLs with expiration"""
        if not value:
            return None
            
        if not hasattr(value, 'url'):
            return value

        request = self.context.get('request')
        
        # Local development
        if settings.DEBUG:
            if request:
                return request.build_absolute_uri(value.url)
            return value.url
            
        # Production - generate time-limited signed URL
        signer = TimestampSigner()
        signed_path = signer.sign(value.url)
        
        # Use CDN if configured
        base_url = getattr(settings, 'CDN_MEDIA_URL', settings.MEDIA_URL)
        
        return f"{base_url}{signed_path}"


#================================= Base64 File Field ============================================



class Base64FileField(serializers.FileField):
    def to_internal_value(self, data):
        if isinstance(data, six.string_types):
            # Remove base64 header if exists
            if "data:" in data and ";base64," in data:
                _, data = data.split(";base64,")
            try:
                decoded_file = base64.b64decode(data)
            except TypeError:
                self.fail("invalid_file")

            file_name = str(uuid.uuid4())[:12]
            file_extension = "png"  # You can improve this if dynamic detection is needed

            complete_file_name = f"{file_name}.{file_extension}"
            data = ContentFile(decoded_file, name=complete_file_name)

        return super().to_internal_value(data)


#============================= Video Validation Code ======================================

class SecureVideoValidator:
    ALLOWED_EXTENSIONS = ['.mp4', '.mov',]
    BLOCKED_EXTENSIONS = ['.exe', '.js', '.jar', '.php', '.sh']
    ALLOWED_MIME_TYPES = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska']
    MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

    def __init__(self, allowed_extensions=None, allowed_mime_types=None, max_size=None, field_name=None):
        self.allowed_extensions = allowed_extensions or self.ALLOWED_EXTENSIONS
        self.allowed_mime_types = allowed_mime_types or self.ALLOWED_MIME_TYPES
        self.max_size = max_size or self.MAX_FILE_SIZE
        self.field_name = field_name or "Video"

    def __call__(self, value):
        self.validate_extension(value)
        self.validate_blocked_types(value)
        self.validate_file_size(value)
        self.validate_mime_type(value)

        
    def validate_extension(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(
                f"{self.field_name} has invalid file extension '{ext}'. Allowed: {', '.join(self.allowed_extensions)}"
            )

    def validate_blocked_types(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext in self.BLOCKED_EXTENSIONS:
            raise ValidationError(f"{self.field_name} file type '{ext}' is not allowed.")

    def validate_file_size(self, value):
        if value.size > self.max_size:
            raise ValidationError(
                f"{self.field_name} is too large. Max size: {self.max_size / 1024 / 1024:.1f}MB"
            )

    def validate_mime_type(self, value):
        mime_type, _ = mimetypes.guess_type(value.name)
        if mime_type not in self.allowed_mime_types:
            raise ValidationError(
                f"{self.field_name} has invalid MIME type '{mime_type}'. Allowed: {', '.join(self.allowed_mime_types)}")

    
    def clean_filename(self, filename):
      return re.sub(r'[^a-zA-Z0-9_\-.]', '_', filename)
    

    def validate_mime_vs_extension(self, value):
      mime_type, _ = mimetypes.guess_type(value.name)
      ext = os.path.splitext(value.name)[1].lower()

      ext_to_mime = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska'
    }

      expected_mime = ext_to_mime.get(ext)
      if expected_mime and mime_type != expected_mime:
        raise ValidationError(
            f"{self.field_name} file extension does not match its MIME type."
        )


class SecureVideoField(serializers.FileField):


    def __init__(self, **kwargs):

        self.field_display_name = kwargs.pop('field_name', None)
        validator_config = {
            'field_name':self.field_display_name,
            'allowed_extensions': kwargs.pop('allowed_extensions', None),
            'allowed_mime_types': kwargs.pop('allowed_mime_types', None),
            'max_size': kwargs.pop('max_size', None)
        }
        self.validator = SecureVideoValidator(**validator_config)
        
        super().__init__(**kwargs)
        self.validators.append(self.validator)

    def to_representation(self, value):
        if not value:
            return None
        if not hasattr(value, 'url'):
            return str(value)

        request = self.context.get('request')

        # Local dev
        if settings.DEBUG:
            return request.build_absolute_uri(value.url) if request else value.url

        # Production signed URL
        signer = TimestampSigner()
        signed_url = signer.sign(value.url)

        # Use CDN or default media
        base_url = getattr(settings, 'CDN_MEDIA_URL', settings.MEDIA_URL)
        return f"{base_url}{signed_url}"



#=================================== Validate Video Duration Code ========================================


def validate_video_duration(video_file, tutor_duration):
    try:
        # If the video file is uploaded as a temporary file, we can use it directly
        if hasattr(video_file, 'temporary_file_path'):
            video_path = video_file.temporary_file_path()
        else:
            # If the file is in memory, we need to save it temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                for chunk in video_file.chunks():
                    tmp.write(chunk)
                video_path = tmp.name
        
        # Use ffmpeg to extract video duration
        try:
            probe = ffmpeg.probe(video_path, v='error', select_streams='v:0', show_entries='stream=duration')
            video_duration_seconds = float(probe['streams'][0]['duration'])
        except ffmpeg.Error as e:
            raise ValidationError(f"Error extracting video duration: {e.stderr.decode()}")

        # If the duration is 0 or negative, the video may be empty or invalid
        if video_duration_seconds <= 0:
            raise ValidationError("The video appears to be empty or corrupted.")

        # Convert the duration to HH:MM format
        minutes = int(video_duration_seconds // 60)
        hours = minutes // 60
        minutes = minutes % 60
        actual_duration_str = f"{hours:02}:{minutes:02}"

        # Clean up by removing the temporary file if it was created
        if hasattr(video_file, 'temporary_file_path'):
            # No need to delete temp file if it’s not a temporary file path
            pass
        else:
            import os
            os.remove(video_path)

        # Compare the extracted duration with the tutor-provided duration
        if actual_duration_str != tutor_duration:
            raise ValidationError(
                f"The actual video duration is {actual_duration_str}. Please enter this exact duration."
            )

    except Exception as e:
        raise ValidationError(f"Could not validate video duration: {str(e)}")
    
#=================================== Get Hash For File Code ========================================

def get_file_hash(file_obj):
    hasher = hashlib.sha256()
    for chunk in file_obj.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()