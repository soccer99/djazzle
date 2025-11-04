# Custom Connection Tests

This directory contains tests for custom database connections with different drivers.

## Test Files

- `test_psycopg2_connection.py` - Tests for psycopg2 (PostgreSQL sync driver)
- `test_psycopg3_connection.py` - Tests for psycopg3 (PostgreSQL sync and async driver)

## Prerequisites

### Install Test Dependencies

```bash
# Install testcontainers (required for these tests)
pip install testcontainers[postgres]

# OR using uv
uv sync --extra testcontainers
```

### Install Database Drivers

For **psycopg2** tests:
```bash
pip install psycopg2-binary
```

For **psycopg3** tests:
```bash
# Already included in main dependencies
pip install psycopg[binary]
```

For **async support** (pytest-asyncio):
```bash
# Already included in dev dependencies
pip install pytest-asyncio
```

## Running the Tests

### Run all custom connection tests
```bash
pytest tests/test_psycopg2_connection.py tests/test_psycopg3_connection.py -v
```

### Run psycopg2 tests only
```bash
pytest tests/test_psycopg2_connection.py -v
```

### Run psycopg3 sync tests only
```bash
pytest tests/test_psycopg3_connection.py::TestPsycopg3SyncConnection -v
```

### Run psycopg3 async tests only
```bash
pytest tests/test_psycopg3_connection.py::TestPsycopg3AsyncConnection -v
```

## What These Tests Cover

### psycopg2 Tests (`test_psycopg2_connection.py`)
- ✅ Connection detection (verifies psycopg2 is detected correctly)
- ✅ SELECT queries with custom connection
- ✅ INSERT queries
- ✅ INSERT with RETURNING clause (PostgreSQL)
- ✅ UPDATE queries
- ✅ DELETE queries
- ✅ Bulk INSERT operations
- ✅ Verification that sync-only connection is properly marked

### psycopg3 Sync Tests (`test_psycopg3_connection.py::TestPsycopg3SyncConnection`)
- ✅ Connection detection (verifies psycopg3 sync is detected correctly)
- ✅ SELECT queries with custom connection
- ✅ INSERT queries
- ✅ INSERT with RETURNING clause (PostgreSQL)
- ✅ UPDATE queries
- ✅ DELETE queries
- ✅ Bulk INSERT operations

### psycopg3 Async Tests (`test_psycopg3_connection.py::TestPsycopg3AsyncConnection`)
- ✅ Async connection detection (verifies psycopg3 async is detected correctly)
- ✅ Async SELECT queries with await syntax
- ✅ Async INSERT queries
- ✅ Async INSERT with RETURNING clause
- ✅ Async UPDATE queries
- ✅ Async DELETE queries
- ✅ Async bulk INSERT operations
- ✅ Error handling when trying to use sync syntax with async connection

## How the Tests Work

1. **Testcontainers**: Each test module uses testcontainers to spin up a PostgreSQL Docker container
2. **Fixtures**: Connection fixtures create and manage database connections
3. **Table Setup**: Each test creates the necessary tables using raw SQL
4. **Verification**: Tests verify operations using both Djazzle queries and raw SQL queries

## Notes

- Tests are automatically skipped if required dependencies are not installed
- Tests use Docker via testcontainers, so Docker must be running
- Each test class uses its own database connection to ensure isolation
- Async tests require pytest-asyncio to be properly installed
- All tests clean up after themselves (close connections, drop data)

## Troubleshooting

### Tests are skipped
If tests show as "SKIPPED", check that:
1. Docker is running (required for testcontainers)
2. testcontainers is installed: `pip install testcontainers[postgres]`
3. The database driver is installed (psycopg2-binary or psycopg)
4. pytest-asyncio is installed for async tests

### pytest-asyncio warnings
If you see warnings about `pytest.mark.asyncio`, ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

And check that `pyproject.toml` has:
```toml
[tool.pytest_asyncio]
mode = "auto"
```
