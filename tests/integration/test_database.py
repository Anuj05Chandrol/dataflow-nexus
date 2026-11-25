"""Integration tests for PostgreSQL."""

import pytest
from sqlalchemy import text

from configs.database import get_engine

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine():
    database_engine = get_engine()

    yield database_engine

    database_engine.dispose()


def test_database_connection(engine):
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

        assert result == 1


def test_required_tables_exist(engine):
    expected_tables = {
        "customers",
        "products",
        "orders",
        "order_items",
        "payments",
    }

    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'nexus'
                """
            )
        )

        actual_tables = set(result.scalars())

    assert expected_tables.issubset(actual_tables)


def test_database_name(engine):
    with engine.connect() as connection:
        result = connection.execute(text("SELECT current_database()")).scalar_one()

    assert result == "dataflow_nexus"
