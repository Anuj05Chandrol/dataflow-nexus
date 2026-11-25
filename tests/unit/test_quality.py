"""Tests for the ETL data quality engine."""

import pytest

from ingestion.batch.extractor import extract_datasets
from ingestion.generators.config import GeneratorConfig
from ingestion.generators.ecommerce import EcommerceGenerator
from processing.validation.quality import (
    DataQualityError,
    money_to_cents,
    validate_datasets,
)


@pytest.fixture
def datasets(tmp_path):
    config = GeneratorConfig(
        customers=20,
        products=10,
        orders=50,
        output_dir=tmp_path,
    )

    EcommerceGenerator(config).generate_all()

    return extract_datasets(tmp_path)


def test_valid_dataset(datasets):
    report = validate_datasets(datasets)

    assert report["status"] == "passed"
    assert report["total_records"] > 0


def test_missing_column(datasets):
    datasets["customers"] = datasets["customers"].drop(columns=["email"])

    with pytest.raises(DataQualityError):
        validate_datasets(datasets)


def test_duplicate_primary_key(datasets):
    df = datasets["customers"]

    df.loc[1, "customer_id"] = df.loc[0, "customer_id"]

    with pytest.raises(DataQualityError):
        validate_datasets(datasets)


def test_null_value(datasets):
    datasets["customers"].loc[0, "email"] = None

    with pytest.raises(DataQualityError):
        validate_datasets(datasets)


def test_blank_value(datasets):
    datasets["customers"].loc[0, "full_name"] = ""

    with pytest.raises(DataQualityError):
        validate_datasets(datasets)


def test_invalid_foreign_key(datasets):
    datasets["orders"].loc[0, "customer_id"] = "999999"

    with pytest.raises(DataQualityError):
        validate_datasets(datasets)


def test_invalid_quantity(datasets):
    datasets["order_items"].loc[0, "quantity"] = "0"

    with pytest.raises(DataQualityError):
        validate_datasets(datasets)


def test_invalid_order_status(datasets):
    datasets["orders"].loc[0, "status"] = "unknown"

    with pytest.raises(DataQualityError):
        validate_datasets(datasets)


def test_invalid_order_total(datasets):
    datasets["orders"].loc[0, "total_amount"] = "0.01"

    with pytest.raises(DataQualityError):
        validate_datasets(datasets)


def test_invalid_payment_amount(datasets):
    datasets["payments"].loc[0, "amount"] = "0.01"

    with pytest.raises(DataQualityError):
        validate_datasets(datasets)


def test_invalid_timestamp(datasets):
    datasets["orders"].loc[0, "order_date"] = "invalid"

    with pytest.raises(DataQualityError):
        validate_datasets(datasets)


def test_money_precision():
    assert money_to_cents("199.99") == 19999


@pytest.mark.parametrize(
    "value",
    ["-1", "NaN", "Infinity", "abc", "1.001"],
)
def test_invalid_money(value):
    with pytest.raises(DataQualityError):
        money_to_cents(value)
