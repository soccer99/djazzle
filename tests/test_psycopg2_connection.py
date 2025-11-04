"""Tests for psycopg2 custom connections."""

import pytest
from src.djazzle import DjazzleQuery, TableFromModel, eq
from tests.models import User


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(scope="module")
def psycopg2_container():
    """Start a PostgreSQL container for psycopg2 tests."""
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed. Install with: uv sync --extra testcontainers")

    try:
        import psycopg2
    except ImportError:
        pytest.skip("psycopg2 not installed. Install with: pip install psycopg2-binary")

    container = PostgresContainer("postgres:15")

    with container as postgres:
        yield postgres


@pytest.fixture
def psycopg2_connection(psycopg2_container):
    """Create a psycopg2 connection to the test database."""
    import psycopg2

    conn = psycopg2.connect(
        host=psycopg2_container.get_container_host_ip(),
        port=psycopg2_container.get_exposed_port(5432),
        dbname=psycopg2_container.dbname,
        user=psycopg2_container.username,
        password=psycopg2_container.password,
    )

    # Create the users table
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tests_user (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                age INTEGER,
                email VARCHAR(100) NOT NULL,
                username VARCHAR(100) NOT NULL,
                address TEXT
            )
        """)
        conn.commit()

    yield conn

    # Cleanup
    conn.close()


@pytest.fixture
def users_table():
    """Fixture to provide a TableFromModel instance for User."""
    return TableFromModel(User)


class TestPsycopg2Connection:
    """Test psycopg2 custom connections with Djazzle."""

    def test_connection_detection(self, psycopg2_connection):
        """Test that psycopg2 connection is detected correctly."""
        from src.djazzle.connection import ConnectionAdapter

        adapter = ConnectionAdapter(psycopg2_connection)
        assert adapter.conn_type == 'psycopg2'
        assert adapter.is_async is False

    def test_select_query(self, psycopg2_connection, users_table):
        """Test SELECT query with psycopg2 connection."""
        # Insert test data using raw psycopg2
        with psycopg2_connection.cursor() as cur:
            cur.execute(
                "INSERT INTO tests_user (name, age, email, username, address) VALUES (%s, %s, %s, %s, %s)",
                ("Alice", 30, "alice@example.com", "alice", "123 Alice St")
            )
            psycopg2_connection.commit()

        # Query using Djazzle with custom connection
        db = DjazzleQuery(conn=psycopg2_connection)
        results = db.select("name", "age").from_(users_table).where(eq(users_table.name, "Alice"))()

        assert len(results) == 1
        assert results[0]["name"] == "Alice"
        assert results[0]["age"] == 30

    def test_insert_query(self, psycopg2_connection, users_table):
        """Test INSERT query with psycopg2 connection."""
        db = DjazzleQuery(conn=psycopg2_connection)

        # Insert using Djazzle
        db.insert(users_table).values({
            "name": "Bob",
            "age": 25,
            "email": "bob@example.com",
            "username": "bob",
            "address": "456 Bob St"
        })()

        # Verify using raw psycopg2
        with psycopg2_connection.cursor() as cur:
            cur.execute("SELECT name, age FROM tests_user WHERE name = %s", ("Bob",))
            row = cur.fetchone()
            assert row[0] == "Bob"
            assert row[1] == 25

    def test_insert_with_returning(self, psycopg2_connection, users_table):
        """Test INSERT with RETURNING clause."""
        db = DjazzleQuery(conn=psycopg2_connection)

        # Insert with RETURNING
        results = db.insert(users_table).values({
            "name": "Charlie",
            "age": 35,
            "email": "charlie@example.com",
            "username": "charlie",
            "address": "789 Charlie St"
        }).returning()()

        assert len(results) == 1
        assert results[0]["name"] == "Charlie"
        assert results[0]["age"] == 35
        assert results[0]["id"] is not None

    def test_update_query(self, psycopg2_connection, users_table):
        """Test UPDATE query with psycopg2 connection."""
        # Insert test data
        with psycopg2_connection.cursor() as cur:
            cur.execute(
                "INSERT INTO tests_user (name, age, email, username, address) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                ("Dave", 40, "dave@example.com", "dave", "111 Dave St")
            )
            user_id = cur.fetchone()[0]
            psycopg2_connection.commit()

        # Update using Djazzle
        db = DjazzleQuery(conn=psycopg2_connection)
        db.update(users_table).set({"age": 41}).where(eq(users_table.id, user_id))()

        # Verify
        with psycopg2_connection.cursor() as cur:
            cur.execute("SELECT age FROM tests_user WHERE id = %s", (user_id,))
            age = cur.fetchone()[0]
            assert age == 41

    def test_delete_query(self, psycopg2_connection, users_table):
        """Test DELETE query with psycopg2 connection."""
        # Insert test data
        with psycopg2_connection.cursor() as cur:
            cur.execute(
                "INSERT INTO tests_user (name, age, email, username, address) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                ("Eve", 45, "eve@example.com", "eve", "222 Eve St")
            )
            user_id = cur.fetchone()[0]
            psycopg2_connection.commit()

        # Delete using Djazzle
        db = DjazzleQuery(conn=psycopg2_connection)
        db.delete(users_table).where(eq(users_table.id, user_id))()

        # Verify
        with psycopg2_connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tests_user WHERE id = %s", (user_id,))
            count = cur.fetchone()[0]
            assert count == 0

    def test_bulk_insert(self, psycopg2_connection, users_table):
        """Test bulk INSERT with psycopg2 connection."""
        db = DjazzleQuery(conn=psycopg2_connection)

        # Bulk insert
        db.insert(users_table).values([
            {
                "name": f"User{i}",
                "age": 20 + i,
                "email": f"user{i}@example.com",
                "username": f"user{i}",
                "address": f"{i} User St"
            }
            for i in range(5)
        ])()

        # Verify
        results = db.select().from_(users_table)()
        user_names = [r["name"] for r in results if r["name"].startswith("User")]
        assert len(user_names) >= 5

    def test_cannot_use_async_with_psycopg2(self, psycopg2_connection, users_table):
        """Test that async syntax raises error with psycopg2."""
        db = DjazzleQuery(conn=psycopg2_connection)

        # Attempting to await should fail since psycopg2 is sync only
        # We can't actually test this without running in async context,
        # but we can verify the connection is marked as sync
        from src.djazzle.connection import ConnectionAdapter
        adapter = ConnectionAdapter(psycopg2_connection)
        assert adapter.is_async is False
