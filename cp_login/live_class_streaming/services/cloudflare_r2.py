import boto3
from django.conf import settings
from botocore.exceptions import BotoCoreError, ClientError

def generate_r2_signed_url(key: str, expires_in: int = None) -> str:

    if not key:
       raise ValueError("Missing object key for signed URL.")

    expires_in = expires_in or getattr(settings, "R2_SIGNED_URL_EXPIRATION", 3600)

    try:
        s3 = boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY,
        aws_secret_access_key=settings.R2_SECRET_KEY,
        region_name="auto",)

        url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": settings.R2_BUCKET_NAME,
            "Key": key,
        },
        ExpiresIn=expires_in,
    )

        return url

    except (BotoCoreError, ClientError) as e:
        raise Exception(f"Error Generating Signed URL: {str(e)}")