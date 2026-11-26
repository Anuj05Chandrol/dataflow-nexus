import boto3
from botocore.config import Config

from configs.object_storage import get_storage_config


def get_s3_client():
    settings = get_storage_config()

    return boto3.client(
        service_name="s3",
        endpoint_url=settings.endpoint,
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        region_name=settings.region,
        config=Config(
            signature_version="s3v4",
            connect_timeout=5,
            read_timeout=60,
            retries={
                "max_attempts": 3,
                "mode": "standard",
            },
            s3={
                "addressing_style": "path",
            },
        ),
    )


def test_connection() -> bool:
    client = get_s3_client()

    try:
        client.list_buckets()
        return True
    finally:
        client.close()
