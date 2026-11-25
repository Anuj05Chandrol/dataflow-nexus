"""Data quality rules for e-commerce datasets."""

from decimal import Decimal, InvalidOperation

import pandas as pd


class DataQualityError(ValueError):
    """Raised when a dataset fails validation."""


SCHEMAS = {
    "customers": [
        "customer_id",
        "full_name",
        "email",
        "city",
        "created_at",
    ],
    "products": [
        "product_id",
        "product_name",
        "category",
        "unit_price",
        "stock_quantity",
    ],
    "orders": [
        "order_id",
        "customer_id",
        "order_date",
        "status",
        "total_amount",
    ],
    "order_items": [
        "order_item_id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
    ],
    "payments": [
        "payment_id",
        "order_id",
        "payment_method",
        "payment_status",
        "amount",
    ],
}

PRIMARY_KEYS = {
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
    "order_items": "order_item_id",
    "payments": "payment_id",
}

FOREIGN_KEYS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("payments", "order_id", "orders", "order_id"),
]

INTEGER_COLUMNS = {
    "customers": ["customer_id"],
    "products": ["product_id", "stock_quantity"],
    "orders": ["order_id", "customer_id"],
    "order_items": [
        "order_item_id",
        "order_id",
        "product_id",
        "quantity",
    ],
    "payments": ["payment_id", "order_id"],
}

MONEY_COLUMNS = {
    "products": ["unit_price"],
    "orders": ["total_amount"],
    "order_items": ["unit_price"],
    "payments": ["amount"],
}

DATE_COLUMNS = {
    "customers": ["created_at"],
    "orders": ["order_date"],
}


def money_to_cents(value) -> int:
    """Convert a monetary value to integer paise."""

    try:
        amount = Decimal(str(value))

        if not amount.is_finite() or amount < 0:
            raise ValueError("Invalid monetary amount")

        cents = amount * 100

        if cents != cents.to_integral_value():
            raise ValueError("Excess monetary precision")

        return int(cents)

    except (InvalidOperation, ValueError, OverflowError) as exc:
        raise DataQualityError(f"Invalid monetary value: {value}") from exc


def validate_datasets(
    datasets: dict[str, pd.DataFrame],
) -> dict:
    """Validate schemas, keys and business rules."""

    checks = []

    for table, columns in SCHEMAS.items():
        if table not in datasets:
            raise DataQualityError(f"Missing dataset: {table}")

        df = datasets[table]

        if df.empty:
            raise DataQualityError(f"{table}: empty dataset")

        if set(df.columns) != set(columns):
            raise DataQualityError(f"{table}: invalid schema")

        if df.isna().any().any():
            raise DataQualityError(f"{table}: null values detected")

        for column in columns:
            if df[column].astype("string").str.strip().eq("").any():
                raise DataQualityError(f"{table}.{column}: blank values")

        for column in INTEGER_COLUMNS.get(table, []):
            values = df[column].astype("string")

            if not values.str.fullmatch(r"[0-9]+").all():
                raise DataQualityError(f"{table}.{column}: invalid integers")

            numbers = values.map(int)

            minimum = 0 if column == "stock_quantity" else 1

            if (numbers < minimum).any():
                raise DataQualityError(f"{table}.{column}: invalid range")

            if (numbers > 2**63 - 1).any():
                raise DataQualityError(f"{table}.{column}: integer overflow")

        key = PRIMARY_KEYS[table]

        if df[key].map(int).duplicated().any():
            raise DataQualityError(f"{table}: duplicate primary keys")

        for column in MONEY_COLUMNS.get(table, []):
            df[column].map(money_to_cents)

        for column in DATE_COLUMNS.get(table, []):
            dates = pd.to_datetime(
                df[column],
                format="ISO8601",
                utc=True,
                errors="coerce",
            )

            if dates.isna().any():
                raise DataQualityError(f"{table}.{column}: invalid dates")

        checks.append(f"{table}: schema and values")

    for child, child_key, parent, parent_key in FOREIGN_KEYS:
        parent_ids = set(datasets[parent][parent_key].map(int))

        valid = datasets[child][child_key].map(int).isin(parent_ids)

        if not valid.all():
            raise DataQualityError(f"{child}.{child_key}: orphan references")

        checks.append(f"{child}.{child_key}: foreign key")

    customers = datasets["customers"]

    if customers["email"].duplicated().any():
        raise DataQualityError("Duplicate customer emails")

    orders = datasets["orders"]
    items = datasets["order_items"]
    payments = datasets["payments"]

    allowed_orders = {
        "pending",
        "completed",
        "cancelled",
        "shipped",
        "returned",
    }

    allowed_payments = {
        "pending",
        "successful",
        "failed",
        "refunded",
    }

    if not orders["status"].isin(allowed_orders).all():
        raise DataQualityError("Invalid order status")

    if not payments["payment_status"].isin(allowed_payments).all():
        raise DataQualityError("Invalid payment status")

    item_totals = items["unit_price"].map(money_to_cents) * items["quantity"].map(int)

    calculated = item_totals.groupby(items["order_id"].map(int)).sum()

    expected = orders["total_amount"].map(money_to_cents)

    actual = orders["order_id"].map(int).map(calculated)

    if actual.isna().any() or not actual.eq(expected).all():
        raise DataQualityError("Order totals do not match order items")

    checks.append("Order totals reconciled")

    order_amounts = dict(
        zip(
            orders["order_id"].map(int),
            expected,
        )
    )

    payment_order_ids = payments["order_id"].map(int)

    if payment_order_ids.duplicated().any():
        raise DataQualityError("Multiple payments per order")

    if set(payment_order_ids) != set(order_amounts):
        raise DataQualityError("Missing order payments")

    payment_amounts = payments["amount"].map(money_to_cents)

    expected_payments = payment_order_ids.map(order_amounts)

    if not payment_amounts.eq(expected_payments).all():
        raise DataQualityError("Payment amounts do not match orders")

    checks.append("Payment amounts reconciled")

    return {
        "status": "passed",
        "checks": checks,
        "records": {name: len(df) for name, df in datasets.items()},
        "total_records": sum(len(df) for df in datasets.values()),
    }
