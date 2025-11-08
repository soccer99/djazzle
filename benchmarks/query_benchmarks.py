"""
Query performance benchmarks comparing Djazzle vs Django ORM.

Note: Django must be properly configured before importing this module.
Use run_benchmarks.py in the project root for standalone execution.
"""

import os
from tests.models import User
from src.djazzle import TableFromModel, DjazzleQuery, eq, desc, like
from .benchmark_runner import BenchmarkRunner
import django
from django.conf import settings
from typing import Optional


# Global connection objects for psycopg2 and psycopg3
_psycopg2_conn = None
_psycopg3_conn = None


def is_postgres_configured():
    """Check if PostgreSQL is configured as the database backend."""
    from django.conf import settings
    engine = settings.DATABASES['default']['ENGINE']
    return 'postgresql' in engine or 'psycopg' in engine


def get_psycopg2_connection():
    """Get or create a psycopg2 connection using Django settings."""
    global _psycopg2_conn
    if _psycopg2_conn is None:
        if not is_postgres_configured():
            raise RuntimeError("PostgreSQL is not configured. Use --use-postgres flag.")

        import psycopg2
        from django.db import connection
        from django.conf import settings

        # Use Django's connection to get the actual test database name
        # Use connection.ensure_connection() to make sure connection is established
        connection.ensure_connection()

        # Get settings from Django's connection (which points to the test database)
        db_settings = connection.settings_dict

        _psycopg2_conn = psycopg2.connect(
            dbname=db_settings['NAME'],
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            host=db_settings['HOST'],
            port=db_settings['PORT']
        )
        _psycopg2_conn.autocommit = True
    return _psycopg2_conn


def get_psycopg3_connection():
    """Get or create a psycopg3 connection using Django settings."""
    global _psycopg3_conn
    if _psycopg3_conn is None:
        if not is_postgres_configured():
            raise RuntimeError("PostgreSQL is not configured. Use --use-postgres flag.")

        import psycopg
        from django.db import connection
        from django.conf import settings

        # Use Django's connection to get the actual test database name
        # Use connection.ensure_connection() to make sure connection is established
        connection.ensure_connection()

        # Get settings from Django's connection (which points to the test database)
        db_settings = connection.settings_dict

        _psycopg3_conn = psycopg.connect(
            dbname=db_settings['NAME'],
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            host=db_settings['HOST'],
            port=db_settings['PORT'],
            autocommit=True
        )
    return _psycopg3_conn


def close_psycopg_connections():
    """Close psycopg connections."""
    global _psycopg2_conn, _psycopg3_conn
    if _psycopg2_conn:
        _psycopg2_conn.close()
        _psycopg2_conn = None
    if _psycopg3_conn:
        _psycopg3_conn.close()
        _psycopg3_conn = None


def setup_test_data(num_records: int = 10000):
    """Create test data for benchmarks."""
    print(f"Setting up test data: {num_records} records...")

    # Clear existing data
    User.objects.all().delete()

    # Bulk create users
    users_to_create = []
    for i in range(num_records):
        users_to_create.append(
            User(
                name=f"User{i}",
                age=(20 + (i % 60)) if i % 10 != 0 else None,
                email=f"user{i}@email.com",
                username=f"user{i}",
                address=f"user{i}",
            )
        )

    User.objects.bulk_create(users_to_create, batch_size=1000)
    print(f"Created {User.objects.count()} test records\n")


def run_all_benchmarks(
    num_records: int = 10000,
    iterations: int = 100,
    output_dir: str = "benchmark_results",
    use_postgres: bool = False
) -> BenchmarkRunner:
    """
    Run all benchmarks comparing Djazzle and Django ORM.

    Args:
        num_records: Number of records to create for testing
        iterations: Number of iterations per benchmark
        output_dir: Directory to save results
        use_postgres: Whether to include psycopg2/psycopg3 benchmarks (requires PostgreSQL)

    Returns:
        BenchmarkRunner with all results
    """
    # Setup
    num_tests = 10
    setup_test_data(num_records)
    runner = BenchmarkRunner(output_dir=output_dir)

    print("Running benchmarks...\n")

    # Benchmark 1: Select All Records
    print(f"1/{num_tests} Select all records...")

    def django_select_all():
        return list(User.objects.all())

    users_table = TableFromModel(User)

    def djazzle_select_all():
        return DjazzleQuery().select().from_(users_table)()

    # Check if we should run psycopg benchmarks (only if postgres is configured)
    run_psycopg_benchmarks = use_postgres and is_postgres_configured()

    if run_psycopg_benchmarks:
        def djazzle_psycopg2_select_all():
            conn = get_psycopg2_connection()
            return DjazzleQuery(conn=conn).select().from_(users_table)()

        def djazzle_psycopg3_select_all():
            conn = get_psycopg3_connection()
            return DjazzleQuery(conn=conn).select().from_(users_table)()

        runner.run_multi_comparison(
            name="Select All Records",
            description=f"Fetch all {num_records} records from database",
            implementations={
                "Django ORM": django_select_all,
                "Djazzle": djazzle_select_all,
                "Djazzle+psycopg2": djazzle_psycopg2_select_all,
                "Djazzle+psycopg3": djazzle_psycopg3_select_all,
            },
            iterations=iterations // 2,
            warmup=5
        )
    else:
        runner.run_comparison(
            name="Select All Records",
            description=f"Fetch all {num_records} records from database",
            django_func=django_select_all,
            djazzle_func=djazzle_select_all,
            iterations=iterations // 2,
            warmup=5
        )

    # Benchmark 2: Filtered Query (Single Match)
    print(f"2/{num_tests} Filtered query (single match)...")

    def django_filtered_single():
        return list(User.objects.filter(name="User10"))

    def djazzle_filtered_single():
        return DjazzleQuery().select().from_(users_table).where(
            eq(users_table.name, "User10")
        )()

    if run_psycopg_benchmarks:
        def djazzle_psycopg2_filtered_single():
            conn = get_psycopg2_connection()
            return DjazzleQuery(conn=conn).select().from_(users_table).where(
                eq(users_table.name, "User10")
            )()

        def djazzle_psycopg3_filtered_single():
            conn = get_psycopg3_connection()
            return DjazzleQuery(conn=conn).select().from_(users_table).where(
                eq(users_table.name, "User10")
            )()

        runner.run_multi_comparison(
            name="Filtered Query (Single Match)",
            description="WHERE clause returning 1 record",
            implementations={
                "Django ORM": django_filtered_single,
                "Djazzle": djazzle_filtered_single,
                "Djazzle+psycopg2": djazzle_psycopg2_filtered_single,
                "Djazzle+psycopg3": djazzle_psycopg3_filtered_single,
            },
            iterations=iterations,
            warmup=10
        )
    else:
        runner.run_comparison(
            name="Filtered Query (Single Match)",
            description="WHERE clause returning 1 record",
            django_func=django_filtered_single,
            djazzle_func=djazzle_filtered_single,
            iterations=iterations,
            warmup=10
        )

    # Benchmark 3: Select Specific Columns
    print(f"3/{num_tests} Select specific columns...")

    def django_select_columns():
        return list(User.objects.values("id", "name", "email"))

    def djazzle_select_columns():
        return DjazzleQuery().select("id", "name", "email").from_(users_table)()

    if run_psycopg_benchmarks:
        def djazzle_psycopg2_select_columns():
            conn = get_psycopg2_connection()
            return DjazzleQuery(conn=conn).select("id", "name", "email").from_(users_table)()

        def djazzle_psycopg3_select_columns():
            conn = get_psycopg3_connection()
            return DjazzleQuery(conn=conn).select("id", "name", "email").from_(users_table)()

        runner.run_multi_comparison(
            name="Select Specific Columns",
            description=f"Select 3 columns from {num_records} records",
            implementations={
                "Django ORM": django_select_columns,
                "Djazzle": djazzle_select_columns,
                "Djazzle+psycopg2": djazzle_psycopg2_select_columns,
                "Djazzle+psycopg3": djazzle_psycopg3_select_columns,
            },
            iterations=iterations // 2,
            warmup=5
        )
    else:
        runner.run_comparison(
            name="Select Specific Columns",
            description=f"Select 2 columns from {num_records} records",
            django_func=django_select_columns,
            djazzle_func=djazzle_select_columns,
            iterations=iterations // 2,
            warmup=5
        )

    # Benchmark 4: Return Model Instances
    print(f"4/{num_tests} Return 50 rows as model instances...")

    def django_as_models():
        return list(User.objects.all()[:50])

    def djazzle_as_models():
        return DjazzleQuery().select().from_(users_table).as_model().limit(50)()

    runner.run_comparison(
        name="Return 50 Model Instances",
        description="Query returning 50 rows as Django model instances",
        django_func=django_as_models,
        djazzle_func=djazzle_as_models,
        iterations=iterations,
        warmup=10
    )

    # Benchmark 5: First N Records
    print(f"5/{num_tests} First N records...")

    def django_limit():
        return list(User.objects.all()[:100])

    def djazzle_first_100():
        results = DjazzleQuery().select().from_(users_table).limit(100)()
        return results

    if run_psycopg_benchmarks:
        def djazzle_psycopg2_first_100():
            conn = get_psycopg2_connection()
            return DjazzleQuery(conn=conn).select().from_(users_table).limit(100)()

        def djazzle_psycopg3_first_100():
            conn = get_psycopg3_connection()
            return DjazzleQuery(conn=conn).select().from_(users_table).limit(100)()

        runner.run_multi_comparison(
            name="First 100 Records",
            description="Fetch only first 100 records",
            implementations={
                "Django ORM": django_limit,
                "Djazzle": djazzle_first_100,
                "Djazzle+psycopg2": djazzle_psycopg2_first_100,
                "Djazzle+psycopg3": djazzle_psycopg3_first_100,
            },
            iterations=iterations,
            warmup=10
        )
    else:
        runner.run_comparison(
            name="First 100 Records",
            description="Fetch only first 100 records",
            django_func=django_limit,
            djazzle_func=djazzle_first_100,
            iterations=iterations,
            warmup=10
        )

    # Benchmark 6: Order by name desc
    print(f"6/{num_tests} Order by name desc")

    def django_order_by():
        dj_results = list(User.objects.order_by("-name"))
        return dj_results

    def djazzle_order_by():
        dz_results = DjazzleQuery().select().from_(users_table).order_by(desc(users_table.name))()
        return dz_results

    if run_psycopg_benchmarks:
        def djazzle_psycopg2_order_by():
            conn = get_psycopg2_connection()
            return DjazzleQuery(conn=conn).select().from_(users_table).order_by(desc(users_table.name))()

        def djazzle_psycopg3_order_by():
            conn = get_psycopg3_connection()
            return DjazzleQuery(conn=conn).select().from_(users_table).order_by(desc(users_table.name))()

        runner.run_multi_comparison(
            name="Order By",
            description="Order by name descending",
            implementations={
                "Django ORM": django_order_by,
                "Djazzle": djazzle_order_by,
                "Djazzle+psycopg2": djazzle_psycopg2_order_by,
                "Djazzle+psycopg3": djazzle_psycopg3_order_by,
            },
            iterations=iterations,
            warmup=10
        )
    else:
        runner.run_comparison(
            name="Order By",
            description="Order by",
            django_func=django_order_by,
            djazzle_func=djazzle_order_by,
            iterations=iterations,
            warmup=10
        )

    # Benchmark 7: INSERT Single Record
    print(f"7/{num_tests} INSERT single record...")

    # Track IDs to delete later
    django_insert_ids = []
    djazzle_insert_ids = []

    def django_insert():
        user = User.objects.create(
            name="BenchmarkUser",
            age=30,
            email="benchmark@test.com",
            username="benchmark_user",
            address="123 Benchmark St"
        )
        django_insert_ids.append(user.id)
        return [user]

    def djazzle_insert():
        # Note: We can't use returning() for MySQL compatibility
        # So we'll just do the insert without returning
        result = DjazzleQuery().insert(users_table).values({
            "name": "BenchmarkUser",
            "age": 30,
            "email": "benchmark@test.com",
            "username": "benchmark_user",
            "address": "123 Benchmark St"
        })()
        return result

    if run_psycopg_benchmarks:
        def djazzle_psycopg2_insert():
            conn = get_psycopg2_connection()
            result = DjazzleQuery(conn=conn).insert(users_table).values({
                "name": "BenchmarkUser",
                "age": 30,
                "email": "benchmark@test.com",
                "username": "benchmark_user",
                "address": "123 Benchmark St"
            })()
            return result

        def djazzle_psycopg3_insert():
            conn = get_psycopg3_connection()
            result = DjazzleQuery(conn=conn).insert(users_table).values({
                "name": "BenchmarkUser",
                "age": 30,
                "email": "benchmark@test.com",
                "username": "benchmark_user",
                "address": "123 Benchmark St"
            })()
            return result

        runner.run_multi_comparison(
            name="INSERT Single Record",
            description="Insert one record into database",
            implementations={
                "Django ORM": django_insert,
                "Djazzle": djazzle_insert,
                "Djazzle+psycopg2": djazzle_psycopg2_insert,
                "Djazzle+psycopg3": djazzle_psycopg3_insert,
            },
            iterations=iterations,
            warmup=10
        )
    else:
        runner.run_comparison(
            name="INSERT Single Record",
            description="Insert one record into database",
            django_func=django_insert,
            djazzle_func=djazzle_insert,
            iterations=iterations,
            warmup=10
        )

    # Clean up inserted records
    User.objects.filter(name="BenchmarkUser").delete()

    # Benchmark 8: UPDATE Single Record
    print(f"8/{num_tests} UPDATE single record...")

    # Create a record to update
    test_user = User.objects.create(
        name="UpdateTest",
        age=25,
        email="update@test.com",
        username="update_test",
        address="456 Update St"
    )

    def django_update():
        User.objects.filter(id=test_user.id).update(age=26)
        return None

    def djazzle_update():
        result = DjazzleQuery().update(users_table).set({"age": 26}).where(
            eq(users_table.id, test_user.id)
        )()
        return result

    if run_psycopg_benchmarks:
        def djazzle_psycopg2_update():
            conn = get_psycopg2_connection()
            return DjazzleQuery(conn=conn).update(users_table).set({"age": 26}).where(
                eq(users_table.id, test_user.id)
            )()

        def djazzle_psycopg3_update():
            conn = get_psycopg3_connection()
            return DjazzleQuery(conn=conn).update(users_table).set({"age": 26}).where(
                eq(users_table.id, test_user.id)
            )()

        runner.run_multi_comparison(
            name="UPDATE Single Record",
            description="Update one record in database",
            implementations={
                "Django ORM": django_update,
                "Djazzle": djazzle_update,
                "Djazzle+psycopg2": djazzle_psycopg2_update,
                "Djazzle+psycopg3": djazzle_psycopg3_update,
            },
            iterations=iterations,
            warmup=10
        )
    else:
        runner.run_comparison(
            name="UPDATE Single Record",
            description="Update one record in database",
            django_func=django_update,
            djazzle_func=djazzle_update,
            iterations=iterations,
            warmup=10
        )

    # Clean up test user
    test_user.delete()

    # Benchmark 9: Bulk INSERT (100 records)
    print(f"9/{num_tests} Bulk INSERT (100 records)...")

    def django_bulk_insert():
        users = [
            User(
                name=f"BulkUser{i}",
                age=20 + (i % 50),
                email=f"bulk{i}@test.com",
                username=f"bulk_user_{i}",
                address=f"{i} Bulk St"
            )
            for i in range(100)
        ]
        created = User.objects.bulk_create(users)
        # Delete immediately to avoid bloat
        User.objects.filter(name__startswith="BulkUser").delete()
        return created

    def djazzle_bulk_insert():
        values = [
            {
                "name": f"BulkUser{i}",
                "age": 20 + (i % 50),
                "email": f"bulk{i}@test.com",
                "username": f"bulk_user_{i}",
                "address": f"{i} Bulk St"
            }
            for i in range(100)
        ]
        result = DjazzleQuery().insert(users_table).values(values)()
        # Delete immediately to avoid bloat
        User.objects.filter(name__startswith="BulkUser").delete()
        return result

    if run_psycopg_benchmarks:
        def djazzle_psycopg2_bulk_insert():
            conn = get_psycopg2_connection()
            values = [
                {
                    "name": f"BulkUser{i}",
                    "age": 20 + (i % 50),
                    "email": f"bulk{i}@test.com",
                    "username": f"bulk_user_{i}",
                    "address": f"{i} Bulk St"
                }
                for i in range(100)
            ]
            result = DjazzleQuery(conn=conn).insert(users_table).values(values)()
            # Delete immediately to avoid bloat
            User.objects.filter(name__startswith="BulkUser").delete()
            return result

        def djazzle_psycopg3_bulk_insert():
            conn = get_psycopg3_connection()
            values = [
                {
                    "name": f"BulkUser{i}",
                    "age": 20 + (i % 50),
                    "email": f"bulk{i}@test.com",
                    "username": f"bulk_user_{i}",
                    "address": f"{i} Bulk St"
                }
                for i in range(100)
            ]
            result = DjazzleQuery(conn=conn).insert(users_table).values(values)()
            # Delete immediately to avoid bloat
            User.objects.filter(name__startswith="BulkUser").delete()
            return result

        runner.run_multi_comparison(
            name="Bulk INSERT (100 records)",
            description="Insert 100 records in one operation",
            implementations={
                "Django ORM": django_bulk_insert,
                "Djazzle": djazzle_bulk_insert,
                "Djazzle+psycopg2": djazzle_psycopg2_bulk_insert,
                "Djazzle+psycopg3": djazzle_psycopg3_bulk_insert,
            },
            iterations=iterations // 2,  # Fewer iterations for bulk operations
            warmup=5
        )
    else:
        runner.run_comparison(
            name="Bulk INSERT (100 records)",
            description="Insert 100 records in one operation",
            django_func=django_bulk_insert,
            djazzle_func=djazzle_bulk_insert,
            iterations=iterations // 2,  # Fewer iterations for bulk operations
            warmup=5
        )

    # Benchmark 10: Bulk UPDATE (100 records)
    print(f"10/{num_tests} Bulk UPDATE (100 records)...")

    # Create 100 records to update
    bulk_update_users = []
    for i in range(100):
        bulk_update_users.append(
            User(
                name=f"UpdateBulk{i}",
                age=20,
                email=f"updatebulk{i}@test.com",
                username=f"update_bulk_{i}",
                address=f"{i} Update St"
            )
        )
    User.objects.bulk_create(bulk_update_users)

    # Get the IDs after creation
    update_user_ids = list(User.objects.filter(name__startswith="UpdateBulk").values_list('id', flat=True))

    def django_bulk_update():
        User.objects.filter(name__startswith="UpdateBulk").update(age=25)
        # Reset for next iteration
        User.objects.filter(name__startswith="UpdateBulk").update(age=20)
        return None

    def djazzle_bulk_update():
        # Update all records with name starting with UpdateBulk
        result = DjazzleQuery().update(users_table).set({"age": 25}).where(
            like(users_table.name, "UpdateBulk%")
        )()
        # Reset for next iteration
        DjazzleQuery().update(users_table).set({"age": 20}).where(
            like(users_table.name, "UpdateBulk%")
        )()
        return result

    if run_psycopg_benchmarks:
        def djazzle_psycopg2_bulk_update():
            conn = get_psycopg2_connection()
            result = DjazzleQuery(conn=conn).update(users_table).set({"age": 25}).where(
                like(users_table.name, "UpdateBulk%")
            )()
            # Reset for next iteration
            DjazzleQuery(conn=conn).update(users_table).set({"age": 20}).where(
                like(users_table.name, "UpdateBulk%")
            )()
            return result

        def djazzle_psycopg3_bulk_update():
            conn = get_psycopg3_connection()
            result = DjazzleQuery(conn=conn).update(users_table).set({"age": 25}).where(
                like(users_table.name, "UpdateBulk%")
            )()
            # Reset for next iteration
            DjazzleQuery(conn=conn).update(users_table).set({"age": 20}).where(
                like(users_table.name, "UpdateBulk%")
            )()
            return result

        runner.run_multi_comparison(
            name="Bulk UPDATE (100 records)",
            description="Update 100 records in one operation",
            implementations={
                "Django ORM": django_bulk_update,
                "Djazzle": djazzle_bulk_update,
                "Djazzle+psycopg2": djazzle_psycopg2_bulk_update,
                "Djazzle+psycopg3": djazzle_psycopg3_bulk_update,
            },
            iterations=iterations // 2,  # Fewer iterations for bulk operations
            warmup=5
        )
    else:
        runner.run_comparison(
            name="Bulk UPDATE (100 records)",
            description="Update 100 records in one operation",
            django_func=django_bulk_update,
            djazzle_func=djazzle_bulk_update,
            iterations=iterations // 2,  # Fewer iterations for bulk operations
            warmup=5
        )

    # Clean up bulk update test records
    User.objects.filter(name__startswith="UpdateBulk").delete()

    # Clean up psycopg connections if they were used
    if run_psycopg_benchmarks:
        close_psycopg_connections()

    print("\nBenchmarks complete!\n")
    return runner
