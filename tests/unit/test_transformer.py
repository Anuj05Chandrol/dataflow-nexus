"""Unit tests for the Parquet transformation engine."""

from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ingestion.batch.extractor import extract_datasets
from ingestion.generators.config import GeneratorConfig
from ingestion.generators.ecommerce import EcommerceGenerator
from processing.transformations.transformer import (
    transform_datasets,
)
from processing.validation.quality import validate_datasets


@pytest.fixture
def transformed_data(tmp_path):
    raw_dir = tmp_path / "raw"
    silver_dir = tmp_path / "silver"

    config = GeneratorConfig(
        customers=20,
        products=10,
        orders=50,
        output_dir=raw_dir,
    )

    EcommerceGenerator(config).generate_all()

    datasets = extract_datasets(raw_dir)

    validate_datasets(datasets)

    transformed = transform_datasets(
        datasets,
        silver_dir,
    )

    return datasets, transformed, silver_dir


def test_all_datasets_transformed(transformed_data):
    _, transformed, _ = transformed_data

    assert len(transformed) == 5


def test_record_counts_preserved(transformed_data):
    raw, transformed, _ = transformed_data

    for table in raw:
        assert len(raw[table]) == len(transformed[table])


def test_parquet_files_created(transformed_data):
    _, transformed, silver_dir = transformed_data

    for table in transformed:
        assert (silver_dir / f"{table}.parquet").is_file()


def test_integer_column_types(transformed_data):
    _, transformed, _ = transformed_data

    assert str(transformed["customers"]["customer_id"].dtype) == "int64"


def test_decimal_precision(transformed_data):
    _, transformed, _ = transformed_data

    value = transformed["products"]["unit_price"].iloc[0]

    assert isinstance(value, Decimal)


def test_timestamp_timezone(transformed_data):
    _, transformed, _ = transformed_data

    assert str(transformed["orders"]["order_date"].dt.tz) == "UTC"


def test_parquet_decimal_schema(transformed_data):
    _, _, silver_dir = transformed_data

    schema = pq.read_schema(silver_dir / "products.parquet")

    assert schema.field("unit_price").type == (pa.decimal128(14, 2))


def test_parquet_record_counts(transformed_data):
    _, transformed, silver_dir = transformed_data

    for table, dataframe in transformed.items():
        parquet = pq.read_table(silver_dir / f"{table}.parquet")

        assert parquet.num_rows == len(dataframe)
