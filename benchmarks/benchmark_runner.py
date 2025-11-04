"""
Professional benchmark runner with statistical analysis and multiple output formats.
"""

import time
import statistics
import json
import csv
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Any, List, Dict
import sys


@dataclass
class BenchmarkResult:
    """Results from a single benchmark."""
    name: str
    description: str
    iterations: int

    # Timing statistics (in milliseconds)
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    p95: float
    p99: float

    # Additional metadata
    records_processed: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class ComparisonResult:
    """Results comparing two implementations."""
    name: str
    description: str
    iterations: int

    # Django ORM stats
    django_mean: float
    django_median: float
    django_std_dev: float

    # Djazzle stats
    djazzle_mean: float
    djazzle_median: float
    djazzle_std_dev: float

    # Comparison metrics
    speedup: float  # Positive means djazzle is faster
    percent_difference: float

    records_processed: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class BenchmarkRunner:
    """Professional benchmark runner with statistical analysis."""

    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[BenchmarkResult] = []
        self.comparisons: List[ComparisonResult] = []

    def run_single(
        self,
        name: str,
        description: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10
    ) -> BenchmarkResult:
        """
        Run a single benchmark with proper warmup and statistical analysis.

        Args:
            name: Benchmark name
            description: Benchmark description
            func: Function to benchmark (should return result for verification)
            iterations: Number of iterations to run
            warmup: Number of warmup iterations

        Returns:
            BenchmarkResult with statistical analysis
        """
        # Warmup phase
        for _ in range(warmup):
            func()

        # Benchmark phase
        timings = []
        result = None
        for _ in range(iterations):
            start = time.perf_counter()
            result = func()
            end = time.perf_counter()
            timings.append((end - start) * 1000)  # Convert to milliseconds

        # Calculate statistics
        timings.sort()
        mean_time = statistics.mean(timings)
        median_time = statistics.median(timings)
        std_dev = statistics.stdev(timings) if len(timings) > 1 else 0
        min_time = min(timings)
        max_time = max(timings)

        # Calculate percentiles
        p95_idx = int(len(timings) * 0.95)
        p99_idx = int(len(timings) * 0.99)
        p95 = timings[p95_idx]
        p99 = timings[p99_idx]

        # Determine records processed
        records_processed = 0
        if result is not None:
            if isinstance(result, list):
                records_processed = len(result)
            elif hasattr(result, 'count'):
                records_processed = result.count()

        benchmark_result = BenchmarkResult(
            name=name,
            description=description,
            iterations=iterations,
            mean=mean_time,
            median=median_time,
            std_dev=std_dev,
            min=min_time,
            max=max_time,
            p95=p95,
            p99=p99,
            records_processed=records_processed,
            timestamp=datetime.now().isoformat()
        )

        self.results.append(benchmark_result)
        return benchmark_result

    def run_comparison(
        self,
        name: str,
        description: str,
        django_func: Callable,
        djazzle_func: Callable,
        iterations: int = 100,
        warmup: int = 10
    ) -> ComparisonResult:
        """
        Run a comparison benchmark between Django ORM and Djazzle.

        Args:
            name: Benchmark name
            description: Benchmark description
            django_func: Django ORM query function
            djazzle_func: Djazzle query function
            iterations: Number of iterations
            warmup: Number of warmup iterations

        Returns:
            ComparisonResult with comparative statistics
        """
        # Run both benchmarks
        django_result = self.run_single(
            f"{name} (Django ORM)",
            description,
            django_func,
            iterations,
            warmup
        )

        djazzle_result = self.run_single(
            f"{name} (Djazzle)",
            description,
            djazzle_func,
            iterations,
            warmup
        )

        # Calculate comparison metrics
        speedup = (django_result.mean - djazzle_result.mean) / django_result.mean
        percent_diff = speedup * 100

        comparison = ComparisonResult(
            name=name,
            description=description,
            iterations=iterations,
            django_mean=django_result.mean,
            django_median=django_result.median,
            django_std_dev=django_result.std_dev,
            djazzle_mean=djazzle_result.mean,
            djazzle_median=djazzle_result.median,
            djazzle_std_dev=djazzle_result.std_dev,
            speedup=speedup,
            percent_difference=percent_diff,
            records_processed=django_result.records_processed,
            timestamp=datetime.now().isoformat()
        )

        self.comparisons.append(comparison)
        return comparison

    def export_json(self, filename: str = None) -> Path:
        """Export results to JSON format."""
        if filename is None:
            filename = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_path = self.output_dir / filename

        data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "python_version": sys.version,
            },
            "results": [r.to_dict() for r in self.results],
            "comparisons": [c.to_dict() for c in self.comparisons]
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        return output_path

    def export_csv(self, filename: str = None) -> Path:
        """Export comparison results to CSV format."""
        if filename is None:
            filename = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        output_path = self.output_dir / filename

        with open(output_path, 'w', newline='') as f:
            if self.comparisons:
                writer = csv.DictWriter(f, fieldnames=self.comparisons[0].to_dict().keys())
                writer.writeheader()
                for comparison in self.comparisons:
                    writer.writerow(comparison.to_dict())

        return output_path

    def export_markdown(self, filename: str = None) -> Path:
        """Export results to Markdown format."""
        if filename is None:
            filename = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        output_path = self.output_dir / filename

        with open(output_path, 'w') as f:
            f.write("# Djazzle Performance Benchmarks\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Python Version:** {sys.version}\n\n")

            if self.comparisons:
                f.write("## Comparison Results\n\n")
                f.write("| Benchmark | Django ORM (ms) | Djazzle (ms) | Speedup | % Difference | Records |\n")
                f.write("|-----------|-----------------|--------------|---------|--------------|----------|\n")

                for comp in self.comparisons:
                    speedup_str = f"{comp.speedup:+.2f}x"
                    percent_str = f"{comp.percent_difference:+.2f}%"

                    f.write(f"| {comp.name} | "
                           f"{comp.django_mean:.4f} ± {comp.django_std_dev:.4f} | "
                           f"{comp.djazzle_mean:.4f} ± {comp.djazzle_std_dev:.4f} | "
                           f"{speedup_str} | "
                           f"{percent_str} | "
                           f"{comp.records_processed} |\n")

                f.write("\n")

            if self.results:
                f.write("## Detailed Results\n\n")
                for result in self.results:
                    f.write(f"### {result.name}\n\n")
                    f.write(f"**Description:** {result.description}\n\n")
                    f.write(f"**Iterations:** {result.iterations}\n\n")
                    f.write("| Metric | Value (ms) |\n")
                    f.write("|--------|------------|\n")
                    f.write(f"| Mean | {result.mean:.4f} |\n")
                    f.write(f"| Median | {result.median:.4f} |\n")
                    f.write(f"| Std Dev | {result.std_dev:.4f} |\n")
                    f.write(f"| Min | {result.min:.4f} |\n")
                    f.write(f"| Max | {result.max:.4f} |\n")
                    f.write(f"| P95 | {result.p95:.4f} |\n")
                    f.write(f"| P99 | {result.p99:.4f} |\n")
                    f.write(f"\n**Records Processed:** {result.records_processed}\n\n")

        return output_path

    def print_summary(self):
        """Print a summary of benchmark results to console."""
        print("\n" + "="*80)
        print("DJAZZLE PERFORMANCE BENCHMARK RESULTS")
        print("="*80 + "\n")

        if self.comparisons:
            print("Comparison Summary:")
            print("-" * 80)
            for comp in self.comparisons:
                print(f"\n{comp.name}")
                print(f"  Description: {comp.description}")
                print(f"  Django ORM:  {comp.django_mean:.4f}ms (± {comp.django_std_dev:.4f}ms)")
                print(f"  Djazzle:     {comp.djazzle_mean:.4f}ms (± {comp.djazzle_std_dev:.4f}ms)")

                if comp.speedup > 0:
                    print(f"  Result:      Djazzle is {abs(comp.percent_difference):.2f}% FASTER")
                else:
                    print(f"  Result:      Djazzle is {abs(comp.percent_difference):.2f}% SLOWER")

                print(f"  Records:     {comp.records_processed}")

        print("\n" + "="*80 + "\n")
