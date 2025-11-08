#!/usr/bin/env python
"""
Standalone benchmark runner that properly sets up Django test database.
"""

import os
import time

import django
from django.conf import settings
from django.test.utils import get_runner
from contextlib import contextmanager

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.test_settings"

@contextmanager
def testcontainers_postgres(enabled: bool):
    """Context manager to optionally start a PostgreSQL Testcontainer

    Args:
        enabled: Whether postgres is enabled

    Yields:
        Container object (or None if not enabled)
        Sets env vars DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        Caller must update settings.DATABASES after django.setup()
    """
    if not enabled:
        yield None
        return

    from testcontainers.postgres import PostgresContainer

    print("Starting PostgreSQL Testcontainer...")
    container = PostgresContainer(
        image="postgres:17", username="test", password="test", dbname="testdb"
    )
    container.start()
    try:
        # Set environment variables for the caller to use
        os.environ["DB_HOST"] = container.get_container_host_ip()
        os.environ["DB_PORT"] = str(container.get_exposed_port(5432))
        os.environ["DB_NAME"] = container.dbname
        os.environ["DB_USER"] = container.username
        os.environ["DB_PASSWORD"] = container.password

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
        "--database",
        choices=["sqlite", "postgres", "mysql"],
        default="sqlite",
        help="Database backend to use (default: sqlite)",
    )
    parser.add_argument(
        "--include-psycopg-tests",
        action="store_true",
        help="Include psycopg2/psycopg3 benchmarks (requires --database=postgres)",
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

    # Validate psycopg tests require postgres
    if args.include_psycopg_tests and args.database != "postgres":
        parser.error("--include-psycopg-tests requires --database=postgres")

    # Set up environment variables for postgres before Django setup
    use_postgres = args.database == "postgres"

    # Configure Django (database settings picked up from environment variables)
    with testcontainers_postgres(use_postgres):
        django.setup()

        if use_postgres:
            print(f"Database configured: postgresql://{os.environ['DB_USER']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}")

        from benchmarks.query_benchmarks import run_all_benchmarks

        # Setup test database
        print("Setting up test database...")
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)
        old_config = test_runner.setup_databases()

        # Debug: Print actual database connection settings
        from django.db import connection
        print(f"Test database settings: {connection.settings_dict['NAME']}")

        # time.sleep(30)

        try:
            # Run benchmarks
            runner = run_all_benchmarks(
                num_records=args.records,
                iterations=args.iterations,
                output_dir=args.output_dir,
                use_postgres=args.include_psycopg_tests,
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
