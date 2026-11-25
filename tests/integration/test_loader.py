"""Integration tests for PostgreSQL bulk ingestion."""

from pathlib import Path

import pytest

from ingestion.batch.extractor import extract_datasets
from ingestion.batch.loader import load_datasets
from processing.transformations.transformer import (
    transform_datasets,
)
from processing.validation.quality import validate_datasets

pytestmark = pytest.mark.integration

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_bulk_loader(tmp_path):
    datasets = extract_datasets(ROOT_DIR / "data" / "raw")

    validate_datasets(datasets)

    transformed = transform_datasets(
        datasets,
        tmp_path / "silver",
    )

    counts = load_datasets(
        transformed,
        tmp_path / "staging",
    )

    expected = {table: len(dataframe) for table, dataframe in datasets.items()}

    assert counts == expected
