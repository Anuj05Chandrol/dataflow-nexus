import logging

from configs.object_storage import get_storage_config
from storage.object_store.buckets import (
    create_buckets,
    list_buckets,
)
from storage.object_store.client import test_connection


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    settings = get_storage_config()

    print("=" * 60)
    print("DATAFLOW NEXUS - OBJECT STORAGE")
    print("=" * 60)

    print(f"Endpoint: {settings.endpoint}")
    print(f"Region: {settings.region}")

    if not test_connection():
        raise RuntimeError("MinIO connection failed.")

    print("\nConnection: SUCCESS")

    print("\nInitializing data lake buckets...")

    results = create_buckets()

    for bucket, status in results.items():
        print(f"  {bucket}: {status}")

    print("\nAvailable buckets:")

    available = list_buckets()

    for bucket in available:
        print(f"  - {bucket}")

    if not set(settings.buckets).issubset(available):
        raise RuntimeError("Required buckets are missing.")

    print("\nObject storage verification: PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
