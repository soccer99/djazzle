# GitHub Actions Workflows

## Test Matrix

The test workflow runs against multiple combinations of:

### Dimensions

- **Python versions**: 3.10, 3.11, 3.12
- **Django versions**: 4.2, 5.0, 5.1, 5.2
- **Database backends**: SQLite, PostgreSQL, MySQL

### Matrix Strategy

To keep CI runtime reasonable while maintaining good coverage, we use a strategic matrix:

**SQLite**: Tested across all Python and Django version combinations
- Most comprehensive coverage
- Fastest to run
- ~12 combinations (3 Python × 4 Django versions)

**PostgreSQL & MySQL**: Only tested on latest Python (3.12) and latest Django (5.2)
- Validates database-specific features
- Ensures compatibility with real databases
- +2 combinations for latest versions

**Total**: ~14 test jobs per CI run

### Why This Strategy?

1. **SQLite tests catch most issues** - Database-agnostic bugs (95%+ of issues)
2. **PostgreSQL/MySQL tests validate specific features** - RETURNING clause, SQL dialect differences
3. **Fast CI** - Full matrix would be 36 jobs (3×4×3), we run 14
4. **Cost-effective** - Fewer jobs means lower GitHub Actions usage

## Services

The workflow defines both PostgreSQL and MySQL service containers at the job level. These are lightweight Docker containers that:

- Start before the test job begins
- Are available to all test runs in the matrix
- Are only actively used when the matrix specifies that backend
- Shut down automatically after the job completes

### PostgreSQL Service
- **Image**: postgres:17
- **Port**: 5432
- **Database**: test_djazzle
- **Credentials**: postgres/postgres

### MySQL Service
- **Image**: mysql:8.0
- **Port**: 3306
- **Database**: test_djazzle
- **Credentials**: root/test

## Environment Variables

Database connection details are set conditionally based on the matrix `db-backend` value:

```yaml
# For PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=test_djazzle
DB_USER=postgres
DB_PASSWORD=postgres

# For MySQL
DB_HOST=localhost
DB_PORT=3306
DB_NAME=test_djazzle
DB_USER=root
DB_PASSWORD=test
```

These are consumed by `tests/conftest.py` to configure Django's database settings.

## Running Locally vs CI

### Local Development
Uses testcontainers to spin up isolated database containers:
```bash
uv run pytest --db postgres
```

### CI (GitHub Actions)
Uses service containers defined in the workflow:
```yaml
pytest --db ${{ matrix.db-backend }}
```

Both approaches use the same test code and fixtures through `tests/conftest.py`.

## Extending the Matrix

To test more combinations, modify the `exclude` section in `.github/workflows/tests.yml`:

```yaml
# To test PostgreSQL on Python 3.11 + Django 5.0, remove:
- python-version: "3.11"
  db-backend: "postgres"
- django-version: "5.0"
  db-backend: "postgres"
```

⚠️ **Warning**: Each additional combination increases CI runtime and cost.

## Coverage Reporting

Coverage is only uploaded once per CI run to avoid duplication:
- Python 3.12
- Django 5.2
- SQLite backend

This provides accurate coverage data without multiple uploads from different database backends running the same code.
