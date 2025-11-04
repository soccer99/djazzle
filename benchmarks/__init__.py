"""
Djazzle Performance Benchmarks

Professional benchmark suite comparing Djazzle query performance against Django ORM.
"""

from .benchmark_runner import BenchmarkRunner, BenchmarkResult
from .query_benchmarks import run_all_benchmarks

__all__ = ["BenchmarkRunner", "BenchmarkResult", "run_all_benchmarks"]
