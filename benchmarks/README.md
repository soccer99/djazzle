# Djazzle Performance Benchmarks

Professional benchmark suite comparing Djazzle query performance against Django ORM.

## Features

- **Statistical Analysis**: Mean, median, standard deviation, min, max, P95, P99
- **Multiple Output Formats**: JSON, CSV, and Markdown reports
- **Warmup Iterations**: Proper warmup phase to ensure JIT compilation and caching
- **Configurable**: Customize number of records, iterations, and output location
- **Professional**: Follows industry-standard benchmarking practices

## Quick Start

Run benchmarks with default settings from the project root:

```bash
python run_benchmarks.py
```

This will:
- Create 10,000 test records
- Run 100 iterations per benchmark
- Output results to `benchmark_results/` directory
- Generate JSON, CSV, and Markdown reports

## Usage

### Basic Command

```bash
python run_benchmarks.py
```

### Custom Configuration

```bash
python run_benchmarks.py \
  --records 50000 \
  --iterations 200 \
  --output-dir my_results \
  --format markdown
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--records` | 10000 | Number of records to create for testing |
| `--iterations` | 100 | Number of iterations per benchmark |
| `--output-dir` | benchmark_results | Directory to save results |
| `--format` | all | Output format: `json`, `csv`, `markdown`, or `all` |

## Benchmarks Included

### 1. Select All Records
Measures performance of fetching all records from the database.

**Django ORM:**
```python
list(User.objects.all())
```

**Djazzle:**
```python
db.select("id", "name", "age").from_(users)()
```

### 2. Filtered Query (Single Match)
Tests WHERE clause performance with a single result.

**Django ORM:**
```python
list(User.objects.filter(name="User5000"))
```

**Djazzle:**
```python
db.select("id", "name", "age").from_(users).where(eq(users.name, "User5000"))()
```

### 3. Select Specific Columns
Compares selecting subset of columns vs all columns.

**Django ORM:**
```python
list(User.objects.values("id", "name"))
```

**Djazzle:**
```python
db.select("id", "name").from_(users)()
```

### 4. Return Model Instances
Measures overhead of materializing Django model instances.

**Django ORM:**
```python
list(User.objects.filter(name="User1000"))
```

**Djazzle:**
```python
db.select("id", "name", "age").from_(users).where(eq(users.name, "User1000")).as_model()()
```

### 5. First N Records
Tests LIMIT clause performance.

**Django ORM:**
```python
list(User.objects.all()[:100])
```

**Djazzle:**
```python
db.select("id", "name", "age").from_(users).limit(100)()
```

## Output Formats

### JSON Format
Complete benchmark data including all statistical metrics:

```json
{
  "metadata": {
    "timestamp": "2024-11-04T12:00:00",
    "python_version": "3.11.0"
  },
  "results": [...],
  "comparisons": [
    {
      "name": "Select All Records",
      "django_mean": 125.4567,
      "djazzle_mean": 98.1234,
      "speedup": 0.218,
      "percent_difference": 21.8
    }
  ]
}
```

### CSV Format
Comparison data in tabular format for easy analysis:

```csv
name,description,iterations,django_mean,djazzle_mean,speedup,percent_difference
Select All Records,Fetch all records,100,125.45,98.12,0.218,21.8
```

### Markdown Format
Human-readable report with formatted tables:

```markdown
# Djazzle Performance Benchmarks

## Comparison Results

| Benchmark | Django ORM (ms) | Djazzle (ms) | Speedup | % Difference |
|-----------|-----------------|--------------|---------|--------------|
| Select All | 125.45 ± 5.23 | 98.12 ± 4.15 | +0.22x | +21.80% |
```

## Understanding Results

### Speedup Metric
- **Positive speedup**: Djazzle is faster than Django ORM
- **Negative speedup**: Django ORM is faster than Djazzle
- **Example**: `+0.22x` means Djazzle is 22% faster

### Statistical Metrics
- **Mean**: Average execution time
- **Median**: Middle value (less affected by outliers)
- **Std Dev**: Consistency of results (lower is more consistent)
- **P95/P99**: 95th/99th percentile (worst-case scenarios)

## Programmatic Usage

You can also use the benchmark runner programmatically:

```python
from benchmarks import BenchmarkRunner

runner = BenchmarkRunner(output_dir="my_results")

# Run a single benchmark
def my_query():
    return list(User.objects.all())

result = runner.run_single(
    name="My Custom Benchmark",
    description="Testing a custom query",
    func=my_query,
    iterations=100
)

# Run a comparison
runner.run_comparison(
    name="Custom Comparison",
    description="Compare two implementations",
    django_func=django_query,
    djazzle_func=djazzle_query,
    iterations=100
)

# Export results
runner.export_json()
runner.export_markdown()
runner.print_summary()
```

## Best Practices

1. **Run with sufficient records**: Use at least 10,000 records for meaningful results
2. **Multiple iterations**: 100+ iterations help smooth out variance
3. **Consistent environment**: Run benchmarks on the same machine/environment
4. **Warmup phase**: Already included to handle JIT compilation
5. **Database state**: Benchmarks automatically reset database state

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Run Performance Benchmarks
  run: |
    python -m benchmarks.query_benchmarks \
      --records 10000 \
      --iterations 50 \
      --format json
```

## Troubleshooting

### "No such table" Error
Ensure Django migrations are applied:
```bash
python runtests.py migrate
```

### Memory Issues with Large Datasets
Reduce the number of records:
```bash
python -m benchmarks.query_benchmarks --records 5000
```

### Inconsistent Results
Increase iterations for more stable statistics:
```bash
python -m benchmarks.query_benchmarks --iterations 200
```

## Contributing

When adding new benchmarks:

1. Add benchmark function to `query_benchmarks.py`
2. Use `runner.run_comparison()` for Django vs Djazzle tests
3. Include clear description of what's being tested
4. Update this README with the new benchmark details
