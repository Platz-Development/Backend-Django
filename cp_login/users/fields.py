# fields.py
import base64
import six
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers

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
