"""Configuration for synthetic e-commerce data."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class GeneratorConfig:
    """Control dataset size and reproducibility."""

    customers: int = 10_000
    products: int = 1_000
    orders: int = 100_000
    seed: int = 42

    output_dir: Path = ROOT_DIR / "data" / "raw"

    start_date: datetime = datetime(2023, 1, 1, tzinfo=timezone.utc)

    end_date: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def __post_init__(self):
        if min(self.customers, self.products, self.orders) < 1:
            raise ValueError("Record counts must be positive.")

        if self.start_date >= self.end_date:
            raise ValueError("Invalid date range.")
