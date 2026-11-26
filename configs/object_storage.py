import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]

load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class ObjectStorageConfig:
    endpoint: str
    access_key: str
    secret_key: str = field(repr=False)
    region: str
    bronze_bucket: str
    silver_bucket: str
    gold_bucket: str

    @property
    def buckets(self) -> tuple[str, ...]:
        return (
            self.bronze_bucket,
            self.silver_bucket,
            self.gold_bucket,
        )


def get_storage_config() -> ObjectStorageConfig:
    access_key = os.getenv("MINIO_ROOT_USER")
    secret_key = os.getenv("MINIO_ROOT_PASSWORD")

    if not access_key or not secret_key:
        raise RuntimeError("MinIO credentials are missing from the environment.")

    return ObjectStorageConfig(
        endpoint=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        access_key=access_key,
        secret_key=secret_key,
        region=os.getenv("MINIO_REGION", "us-east-1"),
        bronze_bucket=os.getenv("MINIO_BRONZE_BUCKET", "nexus-bronze"),
        silver_bucket=os.getenv("MINIO_SILVER_BUCKET", "nexus-silver"),
        gold_bucket=os.getenv("MINIO_GOLD_BUCKET", "nexus-gold"),
    )
