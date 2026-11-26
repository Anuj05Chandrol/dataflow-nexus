from uuid import uuid4

import pytest

from configs.object_storage import get_storage_config
from storage.object_store.buckets import (
    create_buckets,
    list_buckets,
)
from storage.object_store.client import get_s3_client
from storage.object_store.downloader import download_file
from storage.object_store.integrity import calculate_sha256
from storage.object_store.uploader import upload_file

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    s3 = get_s3_client()

    try:
        yield s3
    finally:
        s3.close()


@pytest.fixture
def test_object(client, tmp_path):
    settings = get_storage_config()

    bucket = settings.bronze_bucket
    key = f"tests/{uuid4().hex}.csv"

    source = tmp_path / "integration_sample.csv"

    source.write_bytes(b"id,name\n1,Integration Test\n")

    try:
        yield bucket, key, source

    finally:
        client.delete_object(
            Bucket=bucket,
            Key=key,
        )


def test_minio_connection(client):
    response = client.list_buckets()

    assert "Buckets" in response


def test_required_buckets_exist():
    settings = get_storage_config()

    create_buckets()

    available = list_buckets()

    assert set(settings.buckets).issubset(available)


def test_bucket_initialization_idempotent():
    create_buckets()

    results = create_buckets()

    assert all(value == "already_exists" for value in results.values())


def test_real_file_upload(client, test_object):
    bucket, key, source = test_object

    result = upload_file(
        source,
        bucket,
        key,
    )

    metadata = client.head_object(
        Bucket=bucket,
        Key=key,
    )

    assert result["status"] == "uploaded"

    assert metadata["ContentLength"] == source.stat().st_size


def test_remote_checksum_metadata(client, test_object):
    bucket, key, source = test_object

    upload_file(source, bucket, key)

    metadata = client.head_object(
        Bucket=bucket,
        Key=key,
    )

    assert metadata["Metadata"]["sha256"] == calculate_sha256(source)


def test_upload_download_roundtrip(
    test_object,
    tmp_path,
):
    bucket, key, source = test_object

    uploaded = upload_file(
        source,
        bucket,
        key,
    )

    destination = tmp_path / "downloaded.csv"

    downloaded = download_file(
        bucket,
        key,
        destination,
        uploaded["sha256"],
    )

    assert downloaded["integrity_verified"]

    assert source.read_bytes() == destination.read_bytes()


def test_download_rejects_wrong_checksum(
    test_object,
    tmp_path,
):
    bucket, key, source = test_object

    upload_file(source, bucket, key)

    destination = tmp_path / "invalid.csv"

    with pytest.raises(
        RuntimeError,
        match="Checksum verification failed",
    ):
        download_file(
            bucket,
            key,
            destination,
            "0" * 64,
        )

    assert not destination.exists()


def test_failed_download_preserves_existing_file(
    test_object,
    tmp_path,
):
    bucket, key, source = test_object

    upload_file(source, bucket, key)

    destination = tmp_path / "existing.csv"

    original_content = b"Existing valid file"

    destination.write_bytes(original_content)

    with pytest.raises(RuntimeError):
        download_file(
            bucket,
            key,
            destination,
            "0" * 64,
        )

    assert destination.read_bytes() == original_content
