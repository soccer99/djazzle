"""
Query performance benchmarks comparing Djazzle vs Django ORM.

Note: Django must be properly configured before importing this module.
Use run_benchmarks.py in the project root for standalone execution.
"""

from tests.models import User
from src.djazzle import TableFromModel, DjazzleQuery, eq, desc
from .benchmark_runner import BenchmarkRunner


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
    output_dir: str = "benchmark_results"
) -> BenchmarkRunner:
    """
    Run all benchmarks comparing Djazzle and Django ORM.

    Args:
        num_records: Number of records to create for testing
        iterations: Number of iterations per benchmark
        output_dir: Directory to save results

    Returns:
        BenchmarkRunner with all results
    """
    # Setup
    num_tests = 6
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

    runner.run_comparison(
        name="Select All Records",
        description=f"Fetch all {num_records} records from database",
        django_func=django_select_all,
        djazzle_func=djazzle_select_all,
        iterations=iterations // 2,  # Fewer iterations for large queries
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

    runner.run_comparison(
        name="Order By",
        description="Order by",
        django_func=django_order_by,
        djazzle_func=djazzle_order_by,
        iterations=iterations,
        warmup=10
    )


    print("\nBenchmarks complete!\n")
    return runner


if __name__ == "__main__":
    print("Error: Please use run_benchmarks.py in the project root to run benchmarks.")
    print("\nUsage:")
    print("  python run_benchmarks.py --records 10000 --iterations 100")
    print("\nFor more options:")
    print("  python run_benchmarks.py --help")
    import sys
    sys.exit(1)
