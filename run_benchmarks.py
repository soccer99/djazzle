#!/usr/bin/env python
"""
Standalone benchmark runner that properly sets up Django test database.
"""

import os
import django
from django.conf import settings
from django.test.utils import get_runner
from contextlib import contextmanager


@contextmanager
def optional_postgres_container(enabled: bool):
    """Context manager to optionally start a PostgreSQL Testcontainer."""
    if not enabled:
        yield None
        return

    from testcontainers.postgres import PostgresContainer

    print("Starting PostgreSQL Testcontainer...")
    container = PostgresContainer("postgres:17")
    container.start()
    try:
        # Extract connection info safely
        db_name = container.env.get("POSTGRES_DB", "test")
        db_user = container.env.get("POSTGRES_USER", "postgres")
        db_password = container.env.get("POSTGRES_PASSWORD", "")
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)

        print(f"Using container DB: postgres://{db_user}@{host}:{port}/{db_name}")

        settings.DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": db_name,
                "USER": db_user,
                "PASSWORD": db_password,
                "HOST": host,
                "PORT": port,
            }
        }
        yield container
    finally:
        print("Stopping PostgreSQL Testcontainer...")
        container.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Djazzle performance benchmarks"
    )
    parser.add_argument(
        "--records",
        type=int,
        default=10000,
        help="Number of records to create (default: 10000)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations per benchmark (default: 100)",
    )
    parser.add_argument(
        "--use-postgres",
        action="store_true",
        help="Run benchmarks using PostgreSQL Testcontainer",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results",
        help="Output directory for results (default: benchmark_results)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "markdown", "all"],
        default="all",
        help="Output format (default: all)",
    )

    args = parser.parse_args()

    # Configure Django
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.test_settings"
    django.setup()

    from benchmarks.query_benchmarks import run_all_benchmarks

    with optional_postgres_container(args.use_postgres):
        # Setup test database
        print("Setting up test database...")
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=0, interactive=False, keepdb=True)
        old_config = test_runner.setup_databases()

        try:
            # Run benchmarks
            runner = run_all_benchmarks(
                num_records=args.records,
                iterations=args.iterations,
                output_dir=args.output_dir,
            )

            # Print summary
            runner.print_summary()

            # Export results
            print("Exporting results...")
            if args.format in ["json", "all"]:
                json_path = runner.export_json()
                print(f"  JSON:     {json_path}")

            if args.format in ["csv", "all"]:
                csv_path = runner.export_csv()
                print(f"  CSV:      {csv_path}")

            if args.format in ["markdown", "all"]:
                md_path = runner.export_markdown()
                print(f"  Markdown: {md_path}")

            print("\nDone!")

        finally:
            # Teardown test database
            test_runner.teardown_databases(old_config)
