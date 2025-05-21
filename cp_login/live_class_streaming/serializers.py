from rest_framework import serializers

class LiveClassSessionInitSerializer(serializers.Serializer):
    device_info = serializers.JSONField(required=False)
    client_type = serializers.CharField(
        max_length=20,
        required=False,
        default="web"
    )

    def validate_device_info(self, value):
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("Device info must be a JSON object")
        return value