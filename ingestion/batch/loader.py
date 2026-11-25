"""Bulk-load validated datasets into PostgreSQL."""

import logging
from pathlib import Path

import pandas as pd
from psycopg import sql

from configs.database import get_engine
from ingestion.batch.extractor import TABLES
from processing.validation.quality import SCHEMAS

logger = logging.getLogger(__name__)


def load_datasets(
    datasets: dict[str, pd.DataFrame],
    staging_dir: Path,
) -> dict[str, int]:
    """Atomically replace the development dataset."""

    staging_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for table in TABLES:
        datasets[table][SCHEMAS[table]].to_csv(
            staging_dir / f"{table}.csv",
            index=False,
        )

    engine = get_engine()
    connection = None

    try:
        connection = engine.raw_connection()

        with connection.cursor() as cursor:
            # Replace the existing synthetic snapshot.
            cursor.execute(
                """
                TRUNCATE TABLE
                    nexus.payments,
                    nexus.order_items,
                    nexus.orders,
                    nexus.products,
                    nexus.customers
                """
            )

            for table in TABLES:
                columns = SCHEMAS[table]

                statement = sql.SQL(
                    """
                    COPY {}.{} ({})
                    FROM STDIN
                    WITH (FORMAT CSV, HEADER TRUE)
                    """
                ).format(
                    sql.Identifier("nexus"),
                    sql.Identifier(table),
                    sql.SQL(", ").join(sql.Identifier(column) for column in columns),
                )

                path = staging_dir / f"{table}.csv"

                with cursor.copy(statement) as copy:
                    with path.open("rb") as file:
                        while chunk := file.read(1024 * 1024):
                            copy.write(chunk)

                logger.info(
                    "Loaded %s: %s records",
                    table,
                    f"{len(datasets[table]):,}",
                )

            counts = {}

            for table in TABLES:
                cursor.execute(
                    sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                        sql.Identifier("nexus"),
                        sql.Identifier(table),
                    )
                )

                count = cursor.fetchone()[0]

                if count != len(datasets[table]):
                    raise RuntimeError(f"Row count mismatch: {table}")

                counts[table] = count

        connection.commit()

        return counts

    except Exception:
        if connection is not None:
            connection.rollback()

        raise

    finally:
        if connection is not None:
            connection.close()

        engine.dispose()
