"""Generate reproducible synthetic e-commerce datasets."""

import csv
import random
from datetime import timedelta
from decimal import Decimal

from faker import Faker

from ingestion.generators.config import GeneratorConfig


class EcommerceGenerator:
    """Generate relational e-commerce data."""

    CITIES = [
        "Mumbai",
        "Delhi",
        "Bengaluru",
        "Hyderabad",
        "Chennai",
        "Pune",
        "Kolkata",
        "Ahmedabad",
        "Bhopal",
        "Indore",
        "Surat",
        "Jaipur",
        "Lucknow",
        "Nagpur",
        "Narmadapuram",
    ]

    CATEGORIES = {
        "Electronics": (500, 80_000),
        "Fashion": (200, 5_000),
        "Home and Kitchen": (150, 15_000),
        "Beauty": (100, 3_000),
        "Sports": (200, 12_000),
        "Books": (100, 2_000),
        "Grocery": (50, 1_500),
        "Accessories": (100, 5_000),
    }

    ORDER_STATUSES = [
        "completed",
        "shipped",
        "pending",
        "cancelled",
        "returned",
    ]

    PAYMENT_METHODS = [
        "UPI",
        "Credit Card",
        "Debit Card",
        "Net Banking",
        "Cash on Delivery",
    ]

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.rng = random.Random(config.seed)

        self.fake = Faker("en_IN")
        self.fake.seed_instance(config.seed)

        self.config.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def random_date(self):
        """Generate a timestamp with seasonal sales weighting."""

        seconds = int((self.config.end_date - self.config.start_date).total_seconds())

        while True:
            date = self.config.start_date + timedelta(
                seconds=self.rng.randrange(seconds)
            )

            # Higher sales probability during festive months.
            if date.month in (10, 11, 12):
                return date

            if self.rng.random() < 0.65:
                return date

    def write_csv(self, filename, rows):
        """Export a non-empty dataset to CSV."""

        path = self.config.output_dir / filename

        with path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(rows[0].keys()),
            )

            writer.writeheader()
            writer.writerows(rows)

        print(f"{filename}: {len(rows):,} records")

        return path

    def generate_customers(self):
        """Generate customer master data."""

        customers = []

        for customer_id in range(1, self.config.customers + 1):
            customers.append(
                {
                    "customer_id": customer_id,
                    "full_name": self.fake.name(),
                    "email": (f"customer{customer_id}@example.com"),
                    "city": self.rng.choice(self.CITIES),
                    "created_at": (
                        self.config.start_date
                        - timedelta(days=self.rng.randint(1, 730))
                    ).isoformat(),
                }
            )

        return customers

    def generate_products(self):
        """Generate product master data."""

        products = []

        for product_id in range(1, self.config.products + 1):
            category = self.rng.choice(list(self.CATEGORIES))

            minimum, maximum = self.CATEGORIES[category]

            price = Decimal(
                self.rng.randint(
                    minimum * 100,
                    maximum * 100,
                )
            ) / Decimal("100")

            products.append(
                {
                    "product_id": product_id,
                    "product_name": (f"{category} Product {product_id:05d}"),
                    "category": category,
                    "unit_price": price.quantize(Decimal("0.01")),
                    "stock_quantity": self.rng.randint(0, 500),
                }
            )

        return products

    def generate_transactions(self, products):
        """Generate orders, items and payment records."""

        orders = []
        order_items = []
        payments = []

        item_id = 1

        for order_id in range(1, self.config.orders + 1):
            customer_id = self.rng.randint(1, self.config.customers)

            status = self.rng.choices(
                self.ORDER_STATUSES,
                weights=[70, 12, 8, 6, 4],
                k=1,
            )[0]

            order_date = self.random_date()

            item_count = self.rng.randint(1, min(4, len(products)))

            selected_products = self.rng.sample(
                products,
                item_count,
            )

            total = Decimal("0.00")

            for product in selected_products:
                quantity = self.rng.randint(1, 3)
                price = product["unit_price"]

                total += price * quantity

                order_items.append(
                    {
                        "order_item_id": item_id,
                        "order_id": order_id,
                        "product_id": product["product_id"],
                        "quantity": quantity,
                        "unit_price": price,
                    }
                )

                item_id += 1

            orders.append(
                {
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "order_date": order_date.isoformat(),
                    "status": status,
                    "total_amount": total,
                }
            )

            method = self.rng.choices(
                self.PAYMENT_METHODS,
                weights=[45, 20, 15, 5, 15],
                k=1,
            )[0]

            if status == "returned":
                payment_status = "refunded"
            elif status == "cancelled":
                payment_status = self.rng.choice(["failed", "refunded"])
            elif status == "pending":
                payment_status = "pending"
            elif status == "shipped" and method == "Cash on Delivery":
                payment_status = "pending"
            else:
                payment_status = "successful"

            payments.append(
                {
                    "payment_id": order_id,
                    "order_id": order_id,
                    "payment_method": method,
                    "payment_status": payment_status,
                    "amount": total,
                }
            )

        return orders, order_items, payments

    def generate_all(self):
        """Generate and export all relational datasets."""

        customers = self.generate_customers()
        products = self.generate_products()

        orders, items, payments = self.generate_transactions(products)

        datasets = {
            "customers": customers,
            "products": products,
            "orders": orders,
            "order_items": items,
            "payments": payments,
        }

        for name, rows in datasets.items():
            self.write_csv(f"{name}.csv", rows)

        return {name: len(rows) for name, rows in datasets.items()}
