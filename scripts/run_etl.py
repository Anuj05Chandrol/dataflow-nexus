"""Execute the DataFlow Nexus batch ETL pipeline."""

import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from ingestion.batch.extractor import TABLES, extract_datasets
from ingestion.batch.loader import load_datasets
from processing.transformations.transformer import (
    transform_datasets,
)
from processing.validation.quality import validate_datasets
from scripts.sync_data_lake import sync_data_lake

ROOT_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT_DIR / "data" / "raw"
BRONZE_DIR = ROOT_DIR / "data_lake" / "bronze"
SILVER_DIR = ROOT_DIR / "data_lake" / "silver"
STAGING_DIR = ROOT_DIR / "data" / "processed"
REPORT_DIR = ROOT_DIR / "logs"


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    logger = logging.getLogger(__name__)

    started = time.perf_counter()
    timings = {}

    logger.info("DATAFLOW NEXUS ETL STARTED")

    # Stage 1: Extract and preserve raw data.
    start = time.perf_counter()

    datasets = extract_datasets(RAW_DIR)

    BRONZE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for table in TABLES:
        shutil.copy2(
            RAW_DIR / f"{table}.csv",
            BRONZE_DIR / f"{table}.csv",
        )

    timings["extract"] = time.perf_counter() - start

    # Stage 2: Validate.
    start = time.perf_counter()

    quality_report = validate_datasets(datasets)

    timings["validate"] = time.perf_counter() - start

    logger.info("Data quality checks passed")

    # Stage 3: Transform.
    start = time.perf_counter()

    transformed = transform_datasets(
        datasets,
        SILVER_DIR,
    )

    timings["transform"] = time.perf_counter() - start

    # Stage 4: Load.
    start = time.perf_counter()

    counts = load_datasets(
        transformed,
        STAGING_DIR,
    )

    timings["load"] = time.perf_counter() - start

    total_time = time.perf_counter() - started
    total_records = sum(counts.values())

    raw_bytes = sum((RAW_DIR / f"{table}.csv").stat().st_size for table in TABLES)

    parquet_bytes = sum(
        (SILVER_DIR / f"{table}.parquet").stat().st_size for table in TABLES
    )

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "records": counts,
        "total_records": total_records,
        "execution_seconds": round(total_time, 3),
        "records_per_second": round(total_records / total_time),
        "stage_timings": {key: round(value, 3) for key, value in timings.items()},
        "raw_size_bytes": raw_bytes,
        "parquet_size_bytes": parquet_bytes,
        "storage_reduction_percent": round(
            (1 - parquet_bytes / raw_bytes) * 100,
            2,
        ),
        "data_quality": quality_report,
    }

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = REPORT_DIR / "etl_report.json"

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("DATAFLOW NEXUS ETL COMPLETED")
    print("=" * 60)

    for table, count in counts.items():
        print(f"{table}: {count:,}")

    print("-" * 60)
    print(f"Total records: {total_records:,}")
    print(f"Execution time: {total_time:.2f} seconds")
    print(f"Throughput: {total_records / total_time:,.0f} records/sec")

    for stage, duration in timings.items():
        print(f"{stage}: {duration:.2f} seconds")

    print(f"Raw CSV size: {raw_bytes / 1024**2:.2f} MiB")

    print(f"Parquet size: {parquet_bytes / 1024**2:.2f} MiB")

    print(f"Storage reduction: {report['storage_reduction_percent']}%")

    print(f"Report: {report_path}")
    print("=" * 60)

    storage_report = sync_data_lake()

    print("\nOBJECT STORAGE SYNCHRONIZATION")

    print(f"Uploaded files: {storage_report['total_files']}")

    print(f"Verified files: {storage_report['verified_files']}")

    print(
        f"Storage synchronization time: {storage_report['execution_seconds']} seconds"
    )


if __name__ == "__main__":
    main()
