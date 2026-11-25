"""Unit tests for the synthetic data generator."""

from decimal import Decimal

import pytest

from ingestion.generators.config import GeneratorConfig
from ingestion.generators.ecommerce import EcommerceGenerator


@pytest.fixture
def config(tmp_path):
    return GeneratorConfig(
        customers=100,
        products=50,
        orders=500,
        seed=42,
        output_dir=tmp_path,
    )


@pytest.fixture
def dataset(config):
    generator = EcommerceGenerator(config)

    customers = generator.generate_customers()
    products = generator.generate_products()

    orders, items, payments = generator.generate_transactions(products)

    return customers, products, orders, items, payments


def test_customer_count(dataset):
    customers = dataset[0]
    assert len(customers) == 100


def test_product_count(dataset):
    products = dataset[1]
    assert len(products) == 50


def test_order_count(dataset):
    orders = dataset[2]
    assert len(orders) == 500


def test_payment_count(dataset):
    payments = dataset[4]
    assert len(payments) == 500


def test_unique_customer_ids(dataset):
    customers = dataset[0]

    ids = [row["customer_id"] for row in customers]

    assert len(ids) == len(set(ids))


def test_unique_customer_emails(dataset):
    customers = dataset[0]

    emails = [row["email"] for row in customers]

    assert len(emails) == len(set(emails))


def test_valid_customer_references(dataset):
    customers, _, orders, _, _ = dataset

    customer_ids = {row["customer_id"] for row in customers}

    assert all(order["customer_id"] in customer_ids for order in orders)


def test_valid_product_references(dataset):
    _, products, _, items, _ = dataset

    product_ids = {row["product_id"] for row in products}

    assert all(item["product_id"] in product_ids for item in items)


def test_valid_order_references(dataset):
    _, _, orders, items, payments = dataset

    order_ids = {row["order_id"] for row in orders}

    assert all(item["order_id"] in order_ids for item in items)

    assert all(payment["order_id"] in order_ids for payment in payments)


def test_positive_quantities(dataset):
    items = dataset[3]

    assert all(item["quantity"] > 0 for item in items)


def test_order_totals(dataset):
    _, _, orders, items, _ = dataset

    totals = {}

    for item in items:
        order_id = item["order_id"]

        totals[order_id] = (
            totals.get(order_id, Decimal("0.00"))
            + item["unit_price"] * item["quantity"]
        )

    for order in orders:
        assert order["total_amount"] == totals[order["order_id"]]


def test_payment_amounts(dataset):
    _, _, orders, _, payments = dataset

    order_totals = {row["order_id"]: row["total_amount"] for row in orders}

    assert all(
        payment["amount"] == order_totals[payment["order_id"]] for payment in payments
    )


def test_reproducibility(config):
    first = EcommerceGenerator(config)
    second = EcommerceGenerator(config)

    assert first.generate_customers() == second.generate_customers()

    assert first.generate_products() == second.generate_products()


def test_csv_export(config):
    generator = EcommerceGenerator(config)

    results = generator.generate_all()

    assert len(results) == 5

    for name in results:
        assert (config.output_dir / f"{name}.csv").exists()


def test_invalid_configuration():
    with pytest.raises(ValueError):
        GeneratorConfig(customers=0)
