"""Extract raw e-commerce datasets."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

TABLES = (
    "customers",
    "products",
    "orders",
    "order_items",
    "payments",
)


def extract_datasets(
    source_dir: Path,
) -> dict[str, pd.DataFrame]:
    """Read all required CSV datasets."""

    datasets = {}

    for table in TABLES:
        path = source_dir / f"{table}.csv"

        if not path.is_file():
            raise FileNotFoundError(f"Required dataset missing: {path}")

        dataframe = pd.read_csv(
            path,
            dtype="string",
            keep_default_na=False,
        )

        if dataframe.empty:
            raise ValueError(f"Dataset is empty: {table}")

        datasets[table] = dataframe

        logger.info(
            "Extracted %s: %s records",
            table,
            f"{len(dataframe):,}",
        )

    return datasets
