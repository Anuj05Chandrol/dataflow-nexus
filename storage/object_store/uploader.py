import logging
import mimetypes
from pathlib import Path
from time import perf_counter

from storage.object_store.client import get_s3_client
from storage.object_store.integrity import calculate_sha256

logger = logging.getLogger(__name__)


def upload_file(
    file_path: Path,
    bucket: str,
    object_key: str | None = None,
) -> dict:
    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    object_key = object_key or file_path.name

    file_size = file_path.stat().st_size
    checksum = calculate_sha256(file_path)

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    client = get_s3_client()
    start = perf_counter()

    try:
        client.upload_file(
            Filename=str(file_path),
            Bucket=bucket,
            Key=object_key,
            ExtraArgs={
                "ContentType": content_type,
                "Metadata": {
                    "sha256": checksum,
                    "source-filename": file_path.name,
                },
            },
        )

        metadata = client.head_object(
            Bucket=bucket,
            Key=object_key,
        )

        if metadata["ContentLength"] != file_size:
            raise RuntimeError(f"Object size mismatch: {object_key}")

        if metadata["Metadata"].get("sha256") != checksum:
            raise RuntimeError(f"Checksum metadata mismatch: {object_key}")

        elapsed = perf_counter() - start

        result = {
            "bucket": bucket,
            "object_key": object_key,
            "size_bytes": file_size,
            "sha256": checksum,
            "upload_seconds": round(elapsed, 4),
            "status": "uploaded",
        }

        logger.info(
            "Uploaded %s to s3://%s/%s",
            file_path.name,
            bucket,
            object_key,
        )

        return result

    finally:
        client.close()
