"""Pytest configuration and shared fixtures for Djazzle tests."""

import os
import pytest
from tests.models import User, Pet


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--db",
        action="store",
        default="sqlite",
        choices=["sqlite", "postgres", "mysql"],
        help="Database backend to use for tests (default: sqlite)",
    )


@pytest.fixture(scope="session")
def db_backend(request):
    """Get the selected database backend from command line."""
    return request.config.getoption("--db")


@pytest.fixture(scope="session")
def postgres_container(db_backend):
    """Start a PostgreSQL container if postgres backend is selected."""
    if db_backend != "postgres":
        yield None
        return

    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed. Install with: uv sync --extra testcontainers")

    with PostgresContainer("postgres:15") as postgres:
        # Set environment variables for Django
        os.environ["DB_HOST"] = postgres.get_container_host_ip()
        os.environ["DB_PORT"] = str(postgres.get_exposed_port(5432))
        os.environ["DB_NAME"] = postgres.dbname
        os.environ["DB_USER"] = postgres.username
        os.environ["DB_PASSWORD"] = postgres.password
        yield postgres


@pytest.fixture(scope="session")
def mysql_container(db_backend):
    """Start a MySQL container if mysql backend is selected."""
    if db_backend != "mysql":
        yield None
        return

    try:
        from testcontainers.mysql import MySqlContainer
    except ImportError:
        pytest.skip("testcontainers not installed. Install with: uv sync --extra testcontainers")

    with MySqlContainer("mysql:8.0") as mysql:
        # Set environment variables for Django
        os.environ["DB_HOST"] = mysql.get_container_host_ip()
        os.environ["DB_PORT"] = str(mysql.get_exposed_port(3306))
        os.environ["DB_NAME"] = mysql.dbname
        os.environ["DB_USER"] = mysql.username
        os.environ["DB_PASSWORD"] = mysql.password
        yield mysql


@pytest.fixture(scope="session")
def django_db_modify_db_settings(postgres_container, mysql_container, db_backend):
    """
    Configure Django database settings based on the selected backend.

    This works with both testcontainers (local) and service containers (CI).
    Environment variables are set by:
    - Testcontainers: postgres_container/mysql_container fixtures
    - CI: GitHub Actions workflow
    """
    from django.conf import settings

    if db_backend == "postgres":
        settings.DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.environ.get("DB_NAME", "test_djazzle"),
                "USER": os.environ.get("DB_USER", "postgres"),
                "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
                "HOST": os.environ.get("DB_HOST", "localhost"),
                "PORT": os.environ.get("DB_PORT", "5432"),
            }
        }
    elif db_backend == "mysql":
        settings.DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.mysql",
                "NAME": os.environ.get("DB_NAME", "test_djazzle"),
                "USER": os.environ.get("DB_USER", "root"),
                "PASSWORD": os.environ.get("DB_PASSWORD", "test"),
                "HOST": os.environ.get("DB_HOST", "localhost"),
                "PORT": os.environ.get("DB_PORT", "3306"),
                "OPTIONS": {
                    "charset": "utf8mb4",
                },
            }
        }
    else:  # sqlite (default)
        settings.DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        }


@pytest.fixture
def users_table():
    """Fixture to provide a TableFromModel instance for User."""
    from src.djazzle import TableFromModel
    return TableFromModel(User)


@pytest.fixture
def pets_table():
    """Fixture to provide a TableFromModel instance for Pet."""
    from src.djazzle import TableFromModel
    return TableFromModel(Pet)


@pytest.fixture
def db():
    """Fixture to provide a DjazzleQuery instance."""
    from src.djazzle import DjazzleQuery
    return DjazzleQuery()


@pytest.fixture
def sample_users():
    """Create sample users for testing."""
    User.objects.create(
        name="Alice",
        age=30,
        email="alice@example.com",
        username="alice",
        address="123 Alice St"
    )
    User.objects.create(
        name="Bob",
        age=None,
        email="bob@example.com",
        username="bob",
        address="456 Bob St"
    )
    yield
    # Cleanup happens automatically with pytest-django's transactional tests
