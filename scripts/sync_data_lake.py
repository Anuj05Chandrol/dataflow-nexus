import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from configs.object_storage import get_storage_config
from storage.object_store.buckets import create_buckets
from storage.object_store.downloader import download_file
from storage.object_store.uploader import upload_file

ROOT_DIR = Path(__file__).resolve().parents[1]

BRONZE_DIR = ROOT_DIR / "data_lake" / "bronze"
SILVER_DIR = ROOT_DIR / "data_lake" / "silver"
REPORT_DIR = ROOT_DIR / "logs"

TABLES = (
    "customers",
    "products",
    "orders",
    "order_items",
    "payments",
)

logger = logging.getLogger(__name__)


def sync_data_lake() -> dict:
    start = perf_counter()

    settings = get_storage_config()

    layers = (
        (
            "bronze",
            BRONZE_DIR,
            settings.bronze_bucket,
            ".csv",
        ),
        (
            "silver",
            SILVER_DIR,
            settings.silver_bucket,
            ".parquet",
        ),
    )

    # Validate all required local files before uploading.
    for _, directory, _, extension in layers:
        for table in TABLES:
            file_path = directory / f"{table}{extension}"

            if not file_path.is_file():
                raise FileNotFoundError(file_path)

    create_buckets()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "layers": {},
        "total_files": 0,
        "total_bytes": 0,
        "verified_files": 0,
    }

    with TemporaryDirectory() as temp_dir:
        verification_dir = Path(temp_dir)

        for layer, directory, bucket, extension in layers:
            layer_start = perf_counter()

            layer_report = {
                "bucket": bucket,
                "files": [],
                "total_files": 0,
                "total_bytes": 0,
            }

            for table in TABLES:
                file_path = directory / f"{table}{extension}"

                upload_result = upload_file(
                    file_path=file_path,
                    bucket=bucket,
                )

                verification_result = download_file(
                    bucket=bucket,
                    object_key=file_path.name,
                    destination=(verification_dir / layer / file_path.name),
                    expected_checksum=(upload_result["sha256"]),
                )

                upload_result["integrity_verified"] = verification_result[
                    "integrity_verified"
                ]

                upload_result["download_seconds"] = verification_result[
                    "download_seconds"
                ]

                layer_report["files"].append(upload_result)

                layer_report["total_files"] += 1

                layer_report["total_bytes"] += upload_result["size_bytes"]

                report["verified_files"] += 1

            layer_report["execution_seconds"] = round(
                perf_counter() - layer_start,
                4,
            )

            report["layers"][layer] = layer_report

            report["total_files"] += layer_report["total_files"]

            report["total_bytes"] += layer_report["total_bytes"]

    elapsed = perf_counter() - start

    report["execution_seconds"] = round(elapsed, 4)

    report["total_size_mib"] = round(
        report["total_bytes"] / (1024 * 1024),
        4,
    )

    report["status"] = "success"

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = REPORT_DIR / "object_storage_report.json"

    report_path.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )

    return report


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    report = sync_data_lake()

    print("\n" + "=" * 60)
    print("DATAFLOW NEXUS - DATA LAKE SYNCHRONIZATION")
    print("=" * 60)

    for layer, details in report["layers"].items():
        print(f"\nLayer: {layer.upper()}")
        print(f"Bucket: {details['bucket']}")
        print(f"Files: {details['total_files']}")

        size_mib = details["total_bytes"] / (1024 * 1024)

        print(f"Size: {size_mib:.2f} MiB")

    print("\n" + "-" * 60)

    print(f"Total files: {report['total_files']}")
    print(f"Verified files: {report['verified_files']}")
    print(f"Total size: {report['total_size_mib']} MiB")
    print(f"Execution time: {report['execution_seconds']} seconds")
    print(f"Status: {report['status'].upper()}")

    print("=" * 60)


if __name__ == "__main__":
    main()
