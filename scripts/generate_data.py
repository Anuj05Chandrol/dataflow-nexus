"""Command-line interface for dataset generation."""

import argparse
import time
from pathlib import Path

from ingestion.generators.config import GeneratorConfig
from ingestion.generators.ecommerce import EcommerceGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate DataFlow Nexus datasets.")

    parser.add_argument(
        "--customers",
        type=int,
        default=10_000,
    )

    parser.add_argument(
        "--products",
        type=int,
        default=1_000,
    )

    parser.add_argument(
        "--orders",
        type=int,
        default=100_000,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=GeneratorConfig().output_dir,
    )

    args = parser.parse_args()

    config = GeneratorConfig(
        customers=args.customers,
        products=args.products,
        orders=args.orders,
        seed=args.seed,
        output_dir=args.output,
    )

    print("=" * 60)
    print("DATAFLOW NEXUS - SYNTHETIC DATA ENGINE")
    print("=" * 60)

    start = time.perf_counter()

    generator = EcommerceGenerator(config)
    results = generator.generate_all()

    elapsed = time.perf_counter() - start
    total = sum(results.values())

    print("=" * 60)
    print(f"Total records: {total:,}")
    print(f"Execution time: {elapsed:.2f} seconds")
    print(f"Throughput: {total / elapsed:,.0f} records/sec")
    print(f"Output directory: {config.output_dir.resolve()}")
    print("DATA GENERATION COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
