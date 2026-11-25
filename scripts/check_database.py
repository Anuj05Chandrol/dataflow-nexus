"""Check DataFlow Nexus database connectivity."""

from sqlalchemy import text

from configs.database import get_engine


def main():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            database = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

            tables = (
                connection.execute(
                    text(
                        """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'nexus'
                    ORDER BY table_name
                    """
                    )
                )
                .scalars()
                .all()
            )

            print("=" * 50)
            print("DATAFLOW NEXUS DATABASE CHECK")
            print("=" * 50)

            print("Connection: SUCCESS")
            print(f"Database: {database}")
            print(f"Tables found: {len(tables)}")

            for table in tables:
                print(f"  - {table}")

            expected = {
                "customers",
                "products",
                "orders",
                "order_items",
                "payments",
            }

            if not expected.issubset(set(tables)):
                raise RuntimeError("Required database tables are missing.")

            print("=" * 50)
            print("DATABASE CHECK PASSED")
            print("=" * 50)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
