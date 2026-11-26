import hashlib
from unittest.mock import MagicMock

import pytest

from configs.object_storage import get_storage_config
from storage.object_store.buckets import create_buckets
from storage.object_store.downloader import download_file
from storage.object_store.integrity import (
    calculate_sha256,
    verify_checksum,
)
from storage.object_store.uploader import upload_file


@pytest.fixture
def sample_file(tmp_path):
    file_path = tmp_path / "sample.csv"

    file_path.write_bytes(b"id,name\n1,Test Customer\n")

    return file_path


def test_sha256_correctness(sample_file):
    expected = hashlib.sha256(sample_file.read_bytes()).hexdigest()

    assert calculate_sha256(sample_file) == expected


def test_sha256_length(sample_file):
    assert len(calculate_sha256(sample_file)) == 64


def test_sha256_deterministic(sample_file):
    first = calculate_sha256(sample_file)
    second = calculate_sha256(sample_file)

    assert first == second


def test_sha256_detects_changes(sample_file):
    original = calculate_sha256(sample_file)

    sample_file.write_bytes(b"Modified content")

    assert calculate_sha256(sample_file) != original


def test_sha256_empty_file(tmp_path):
    file_path = tmp_path / "empty.txt"
    file_path.write_bytes(b"")

    expected = hashlib.sha256(b"").hexdigest()

    assert calculate_sha256(file_path) == expected


def test_sha256_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        calculate_sha256(tmp_path / "missing.csv")


def test_checksum_verification_success(sample_file):
    checksum = calculate_sha256(sample_file)

    assert verify_checksum(sample_file, checksum)


def test_checksum_verification_failure(sample_file):
    assert not verify_checksum(
        sample_file,
        "0" * 64,
    )


def test_checksum_case_insensitive(sample_file):
    checksum = calculate_sha256(sample_file)

    assert verify_checksum(
        sample_file,
        checksum.upper(),
    )


def test_storage_configuration(monkeypatch):
    monkeypatch.setenv("MINIO_ROOT_USER", "test_user")

    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "test_password")

    monkeypatch.setenv("MINIO_ENDPOINT", "http://localhost:9000")

    settings = get_storage_config()

    assert settings.access_key == "test_user"
    assert settings.secret_key == "test_password"
    assert settings.endpoint == "http://localhost:9000"


def test_missing_storage_credentials(monkeypatch):
    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)

    monkeypatch.delenv("MINIO_ROOT_PASSWORD", raising=False)

    with pytest.raises(RuntimeError):
        get_storage_config()


def test_storage_bucket_configuration(monkeypatch):
    monkeypatch.setenv("MINIO_ROOT_USER", "test")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "test_password")

    monkeypatch.setenv("MINIO_BRONZE_BUCKET", "test-bronze")

    monkeypatch.setenv("MINIO_SILVER_BUCKET", "test-silver")

    monkeypatch.setenv("MINIO_GOLD_BUCKET", "test-gold")

    settings = get_storage_config()

    assert settings.buckets == (
        "test-bronze",
        "test-silver",
        "test-gold",
    )


def test_secret_not_exposed_in_repr(monkeypatch):
    monkeypatch.setenv("MINIO_ROOT_USER", "test")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "private_password")

    settings = get_storage_config()

    assert "private_password" not in repr(settings)


def test_upload_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        upload_file(
            tmp_path / "missing.csv",
            "test-bucket",
        )


def test_upload_success(sample_file, monkeypatch):
    client = MagicMock()

    checksum = calculate_sha256(sample_file)

    client.head_object.return_value = {
        "ContentLength": sample_file.stat().st_size,
        "Metadata": {
            "sha256": checksum,
        },
    }

    monkeypatch.setattr(
        "storage.object_store.uploader.get_s3_client",
        lambda: client,
    )

    result = upload_file(
        sample_file,
        "test-bucket",
    )

    assert result["status"] == "uploaded"
    assert result["sha256"] == checksum
    assert result["object_key"] == sample_file.name

    client.upload_file.assert_called_once()
    client.close.assert_called_once()


def test_upload_size_mismatch(sample_file, monkeypatch):
    client = MagicMock()

    client.head_object.return_value = {
        "ContentLength": 0,
        "Metadata": {
            "sha256": calculate_sha256(sample_file),
        },
    }

    monkeypatch.setattr(
        "storage.object_store.uploader.get_s3_client",
        lambda: client,
    )

    with pytest.raises(
        RuntimeError,
        match="Object size mismatch",
    ):
        upload_file(sample_file, "test-bucket")

    client.close.assert_called_once()


def test_upload_checksum_mismatch(
    sample_file,
    monkeypatch,
):
    client = MagicMock()

    client.head_object.return_value = {
        "ContentLength": sample_file.stat().st_size,
        "Metadata": {
            "sha256": "invalid",
        },
    }

    monkeypatch.setattr(
        "storage.object_store.uploader.get_s3_client",
        lambda: client,
    )

    with pytest.raises(
        RuntimeError,
        match="Checksum metadata mismatch",
    ):
        upload_file(sample_file, "test-bucket")


def test_download_corruption_detected(
    tmp_path,
    monkeypatch,
):
    client = MagicMock()

    client.head_object.return_value = {
        "ContentLength": 7,
        "Metadata": {
            "sha256": "0" * 64,
        },
    }

    def fake_download(Bucket, Key, Filename):
        from pathlib import Path

        Path(Filename).write_bytes(b"corrupt")

    client.download_file.side_effect = fake_download

    monkeypatch.setattr(
        "storage.object_store.downloader.get_s3_client",
        lambda: client,
    )

    destination = tmp_path / "download.csv"

    with pytest.raises(
        RuntimeError,
        match="Checksum verification failed",
    ):
        download_file(
            "test-bucket",
            "sample.csv",
            destination,
        )

    assert not destination.exists()
    assert not list(tmp_path.glob("*.part"))


def test_bucket_creation_idempotent(monkeypatch):
    settings = get_storage_config()

    client = MagicMock()

    client.list_buckets.return_value = {
        "Buckets": [{"Name": bucket} for bucket in settings.buckets]
    }

    monkeypatch.setattr(
        "storage.object_store.buckets.get_s3_client",
        lambda: client,
    )

    results = create_buckets()

    assert all(status == "already_exists" for status in results.values())

    client.create_bucket.assert_not_called()
    client.close.assert_called_once()
