"""Transform raw datasets into typed Parquet files."""

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from processing.validation.quality import (
    DATE_COLUMNS,
    INTEGER_COLUMNS,
    MONEY_COLUMNS,
    SCHEMAS,
)


def transform_datasets(
    datasets: dict[str, pd.DataFrame],
    output_dir: Path,
) -> dict[str, pd.DataFrame]:
    """Apply explicit data types and write Parquet."""

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    transformed = {}

    for name, raw in datasets.items():
        df = raw[SCHEMAS[name]].copy()

        for column in INTEGER_COLUMNS.get(name, []):
            df[column] = df[column].astype("int64")

        for column in MONEY_COLUMNS.get(name, []):
            df[column] = df[column].map(
                lambda value: Decimal(str(value)).quantize(Decimal("0.01"))
            )

        for column in DATE_COLUMNS.get(name, []):
            df[column] = pd.to_datetime(
                df[column],
                utc=True,
                errors="raise",
            )

        arrow_table = pa.Table.from_pandas(
            df,
            preserve_index=False,
        )

        for column in MONEY_COLUMNS.get(name, []):
            index = arrow_table.schema.get_field_index(column)

            arrow_table = arrow_table.set_column(
                index,
                column,
                pa.array(
                    df[column].tolist(),
                    type=pa.decimal128(14, 2),
                ),
            )

        path = output_dir / f"{name}.parquet"

        pq.write_table(
            arrow_table,
            path,
            compression="snappy",
        )

        transformed[name] = df

    return transformed
