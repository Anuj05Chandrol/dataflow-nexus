import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter

from storage.object_store.client import get_s3_client
from storage.object_store.integrity import calculate_sha256

logger = logging.getLogger(__name__)


def download_file(
    bucket: str,
    object_key: str,
    destination: Path,
    expected_checksum: str | None = None,
) -> dict:
    destination = Path(destination)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = get_s3_client()
    start = perf_counter()
    temporary_path = None

    try:
        metadata = client.head_object(
            Bucket=bucket,
            Key=object_key,
        )

        stored_checksum = metadata["Metadata"].get("sha256")

        expected_checksum = expected_checksum or stored_checksum

        if not expected_checksum:
            raise RuntimeError(f"Missing checksum: {object_key}")

        with NamedTemporaryFile(
            dir=destination.parent,
            suffix=".part",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        client.download_file(
            Bucket=bucket,
            Key=object_key,
            Filename=str(temporary_path),
        )

        actual_checksum = calculate_sha256(temporary_path)

        if actual_checksum != expected_checksum:
            raise RuntimeError(f"Checksum verification failed: {object_key}")

        if temporary_path.stat().st_size != metadata["ContentLength"]:
            raise RuntimeError(f"Downloaded size mismatch: {object_key}")

        temporary_path.replace(destination)

        elapsed = perf_counter() - start

        logger.info(
            "Downloaded and verified s3://%s/%s",
            bucket,
            object_key,
        )

        return {
            "bucket": bucket,
            "object_key": object_key,
            "destination": str(destination),
            "size_bytes": destination.stat().st_size,
            "sha256": actual_checksum,
            "download_seconds": round(elapsed, 4),
            "integrity_verified": True,
            "status": "downloaded",
        }

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

        client.close()
