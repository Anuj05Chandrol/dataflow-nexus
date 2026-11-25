"""Verify the loaded ETL snapshot."""

from pathlib import Path

import pytest
from sqlalchemy import text

from configs.database import get_engine
from ingestion.batch.extractor import extract_datasets

pytestmark = pytest.mark.integration

ROOT_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def engine():
    database_engine = get_engine()

    yield database_engine

    database_engine.dispose()


def test_loaded_record_counts(engine):
    datasets = extract_datasets(ROOT_DIR / "data" / "raw")

    with engine.connect() as connection:
        for table, dataframe in datasets.items():
            count = connection.execute(
                text(f"SELECT COUNT(*) FROM nexus.{table}")
            ).scalar_one()

            assert count == len(dataframe)


def test_database_order_reconciliation(engine):
    with engine.connect() as connection:
        mismatches = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM nexus.orders o
                LEFT JOIN (
                    SELECT
                        order_id,
                        SUM(quantity * unit_price) AS total
                    FROM nexus.order_items
                    GROUP BY order_id
                ) i ON o.order_id = i.order_id
                WHERE o.total_amount IS DISTINCT FROM i.total
                """
            )
        ).scalar_one()

    assert mismatches == 0


def test_database_payment_reconciliation(engine):
    with engine.connect() as connection:
        mismatches = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM nexus.orders o
                LEFT JOIN nexus.payments p
                    ON o.order_id = p.order_id
                WHERE o.total_amount IS DISTINCT FROM p.amount
                """
            )
        ).scalar_one()

    assert mismatches == 0
