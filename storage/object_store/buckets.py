import logging

from configs.object_storage import get_storage_config
from storage.object_store.client import get_s3_client

logger = logging.getLogger(__name__)


def create_buckets() -> dict[str, str]:
    settings = get_storage_config()
    client = get_s3_client()

    results = {}

    try:
        existing = {bucket["Name"] for bucket in client.list_buckets()["Buckets"]}

        for bucket in settings.buckets:
            if bucket in existing:
                results[bucket] = "already_exists"

                logger.info("Bucket already exists: %s", bucket)
                continue

            client.create_bucket(Bucket=bucket)

            results[bucket] = "created"

            logger.info("Created bucket: %s", bucket)

        return results

    finally:
        client.close()


def list_buckets() -> list[str]:
    client = get_s3_client()

    try:
        response = client.list_buckets()

        return sorted(bucket["Name"] for bucket in response["Buckets"])
    finally:
        client.close()
