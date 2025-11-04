# Testing Guide

Djazzle uses pytest with support for testing against multiple database backends using testcontainers.

## Quick Start

### Run tests with SQLite (default)

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_select.py

# Run with coverage
uv run pytest --cov=src/djazzle --cov-report=term
```

### Run tests with PostgreSQL

```bash
# Install testcontainers extra
uv sync --extra testcontainers

# Run tests against PostgreSQL container
uv run pytest --db postgres

# Run specific test file
uv run pytest tests/test_insert.py --db postgres
```

### Run tests with MySQL

```bash
# Install testcontainers extra
uv sync --extra testcontainers

# Run tests against MySQL container
uv run pytest --db mysql

# Run specific test file
uv run pytest tests/test_update.py --db mysql
```

## Test Organization

Tests are organized by operation type:

- `test_select.py` - SELECT queries, aliases, and JOINs
- `test_insert.py` - INSERT operations
- `test_update.py` - UPDATE operations
- `test_delete.py` - DELETE operations
- `test_async.py` - Async query execution

## Database Backends

### SQLite (Default)

SQLite is the default database backend for tests. It requires no additional setup and uses an in-memory database.

**Pros:**
- No dependencies
- Fast startup
- Perfect for quick local testing

**Cons:**
- Some features not supported (e.g., `RETURNING` clause, `DELETE...LIMIT`)
- May behave differently than PostgreSQL/MySQL in production

### PostgreSQL (via testcontainers)

PostgreSQL tests run against a real PostgreSQL container managed by testcontainers.

**Pros:**
- Tests real PostgreSQL behavior
- Supports all PostgreSQL features (RETURNING, etc.)
- Automatic container management
- Clean state for each test session

**Cons:**
- Requires Docker
- Slower startup (~2-5 seconds for container initialization)
- Requires testcontainers extra: `uv sync --extra testcontainers`

**Container Details:**
- Image: `postgres:15`
- Auto-generated credentials
- Ephemeral (destroyed after tests)

### MySQL (via testcontainers)

MySQL tests run against a real MySQL container managed by testcontainers.

**Pros:**
- Tests real MySQL behavior
- Automatic container management
- Clean state for each test session

**Cons:**
- Requires Docker
- Slower startup (~10-15 seconds for container initialization)
- Requires testcontainers extra: `uv sync --extra testcontainers`
- Some Djazzle features not supported (MySQL doesn't support `RETURNING`)

**Container Details:**
- Image: `mysql:8.0`
- Auto-generated credentials
- Ephemeral (destroyed after tests)

## Requirements

### For SQLite tests (default)
- Python 3.10+
- Django 4.2+
- No additional dependencies

### For PostgreSQL/MySQL tests
- Python 3.10+
- Django 4.2+
- Docker installed and running
- testcontainers package: `uv sync --extra testcontainers`

## CI/CD Integration

The GitHub Actions workflow (`.github/workflows/tests.yml`) runs tests against PostgreSQL in CI using a PostgreSQL service container. To test multiple databases in CI, you can extend the matrix:

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
    django-version: ["4.2", "5.0", "5.1"]
    db-backend: ["postgres", "mysql"]
```

## Troubleshooting

### "Docker not available" error

Testcontainers requires Docker to be installed and running. Make sure:
1. Docker Desktop is installed
2. Docker daemon is running
3. Your user has permission to access Docker

### "testcontainers not installed" error

Install the testcontainers extra:
```bash
uv sync --extra testcontainers
```

### Container startup timeout

If containers take too long to start, you can increase the timeout in `tests/conftest.py` or check your Docker resource limits.

### Tests fail with "table locked" (SQLite only)

This can happen with async tests on SQLite. The async tests use `@pytest.mark.django_db(transaction=True)` to avoid locking issues.

## Writing Tests

### Use database-specific skipping

Some features are database-specific. Use `skipIf` to skip tests that don't apply:

```python
from unittest import skipIf
from django.db import connection

@skipIf(
    connection.vendor != "postgresql",
    "RETURNING is only supported in PostgreSQL"
)
def test_insert_with_returning(self, db, users_table):
    result = db.insert(users_table).values({...}).returning()()
    assert result[0]["id"] is not None
```

### Async tests

Async tests require proper transaction handling:

```python
@pytest.mark.django_db(transaction=True)
class TestAsyncQueries:
    @pytest.mark.asyncio
    async def test_async_insert(self, db, users_table):
        result = await db.insert(users_table).values({...})
        assert result is None
```

## Performance Tips

1. **Use SQLite for quick local development** - It's fast and requires no setup
2. **Use PostgreSQL/MySQL for integration tests** - Test against real database behavior
3. **Run tests in parallel** with `pytest-xdist` (future enhancement)
4. **Session-scoped containers** - Containers are created once per test session, not per test
