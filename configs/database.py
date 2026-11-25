"""Database configuration for DataFlow Nexus."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

ROOT_DIR = Path(__file__).resolve().parents[1]

load_dotenv(ROOT_DIR / ".env")


def get_database_url() -> URL:
    """Build the PostgreSQL connection URL."""

    password = os.getenv("POSTGRES_PASSWORD")

    if not password:
        raise RuntimeError("POSTGRES_PASSWORD is missing from environment.")

    return URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "nexus_admin"),
        password=password,
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "dataflow_nexus"),
    )


def get_engine():
    """Create a reusable SQLAlchemy database engine."""

    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"connect_timeout": 10},
    )


def test_connection() -> bool:
    """Verify connectivity to PostgreSQL."""

    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()

        return result == 1

    finally:
        engine.dispose()
