"""Tests for psycopg3 custom connections (sync and async)."""

import pytest
import pytest_asyncio
from src.djazzle import DjazzleQuery, TableFromModel, eq
from tests.models import User


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(scope="module")
def psycopg3_container():
    """Start a PostgreSQL container for psycopg3 tests."""
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed. Install with: uv sync --extra testcontainers")

    try:
        import psycopg
    except ImportError:
        pytest.skip("psycopg (version 3) not installed. Install with: pip install psycopg")

    container = PostgresContainer("postgres:15")

    with container as postgres:
        yield postgres


@pytest.fixture
def psycopg3_connection_string(psycopg3_container):
    """Get the connection string for the PostgreSQL container."""
    return (
        f"host={psycopg3_container.get_container_host_ip()} "
        f"port={psycopg3_container.get_exposed_port(5432)} "
        f"dbname={psycopg3_container.dbname} "
        f"user={psycopg3_container.username} "
        f"password={psycopg3_container.password}"
    )


@pytest.fixture
def psycopg3_sync_connection(psycopg3_connection_string):
    """Create a psycopg3 sync connection to the test database."""
    import psycopg

    conn = psycopg.connect(psycopg3_connection_string)

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


class TestPsycopg3SyncConnection:
    """Test psycopg3 sync connections with Djazzle."""

    def test_connection_detection(self, psycopg3_sync_connection):
        """Test that psycopg3 sync connection is detected correctly."""
        from src.djazzle.connection import ConnectionAdapter

        adapter = ConnectionAdapter(psycopg3_sync_connection)
        assert adapter.conn_type == 'psycopg3'
        assert adapter.is_async is False

    def test_select_query(self, psycopg3_sync_connection, users_table):
        """Test SELECT query with psycopg3 sync connection."""
        # Insert test data using raw psycopg3
        with psycopg3_sync_connection.cursor() as cur:
            cur.execute(
                "INSERT INTO tests_user (name, age, email, username, address) VALUES (%s, %s, %s, %s, %s)",
                ("Alice", 30, "alice@example.com", "alice", "123 Alice St")
            )
            psycopg3_sync_connection.commit()

        # Query using Djazzle with custom connection
        db = DjazzleQuery(conn=psycopg3_sync_connection)
        results = db.select("name", "age").from_(users_table).where(eq(users_table.name, "Alice"))()

        assert len(results) == 1
        assert results[0]["name"] == "Alice"
        assert results[0]["age"] == 30

    def test_insert_query(self, psycopg3_sync_connection, users_table):
        """Test INSERT query with psycopg3 sync connection."""
        db = DjazzleQuery(conn=psycopg3_sync_connection)

        # Insert using Djazzle
        db.insert(users_table).values({
            "name": "Bob",
            "age": 25,
            "email": "bob@example.com",
            "username": "bob",
            "address": "456 Bob St"
        })()

        # Verify using raw psycopg3
        with psycopg3_sync_connection.cursor() as cur:
            cur.execute("SELECT name, age FROM tests_user WHERE name = %s", ("Bob",))
            row = cur.fetchone()
            assert row[0] == "Bob"
            assert row[1] == 25

    def test_insert_with_returning(self, psycopg3_sync_connection, users_table):
        """Test INSERT with RETURNING clause."""
        db = DjazzleQuery(conn=psycopg3_sync_connection)

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

    def test_update_query(self, psycopg3_sync_connection, users_table):
        """Test UPDATE query with psycopg3 sync connection."""
        # Insert test data
        with psycopg3_sync_connection.cursor() as cur:
            cur.execute(
                "INSERT INTO tests_user (name, age, email, username, address) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                ("Dave", 40, "dave@example.com", "dave", "111 Dave St")
            )
            user_id = cur.fetchone()[0]
            psycopg3_sync_connection.commit()

        # Update using Djazzle
        db = DjazzleQuery(conn=psycopg3_sync_connection)
        db.update(users_table).set({"age": 41}).where(eq(users_table.id, user_id))()

        # Verify
        with psycopg3_sync_connection.cursor() as cur:
            cur.execute("SELECT age FROM tests_user WHERE id = %s", (user_id,))
            age = cur.fetchone()[0]
            assert age == 41

    def test_delete_query(self, psycopg3_sync_connection, users_table):
        """Test DELETE query with psycopg3 sync connection."""
        # Insert test data
        with psycopg3_sync_connection.cursor() as cur:
            cur.execute(
                "INSERT INTO tests_user (name, age, email, username, address) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                ("Eve", 45, "eve@example.com", "eve", "222 Eve St")
            )
            user_id = cur.fetchone()[0]
            psycopg3_sync_connection.commit()

        # Delete using Djazzle
        db = DjazzleQuery(conn=psycopg3_sync_connection)
        db.delete(users_table).where(eq(users_table.id, user_id))()

        # Verify
        with psycopg3_sync_connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tests_user WHERE id = %s", (user_id,))
            count = cur.fetchone()[0]
            assert count == 0

    def test_bulk_insert(self, psycopg3_sync_connection, users_table):
        """Test bulk INSERT with psycopg3 sync connection."""
        db = DjazzleQuery(conn=psycopg3_sync_connection)

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


class TestPsycopg3AsyncConnection:
    """Test psycopg3 async connections with Djazzle."""

    @pytest_asyncio.fixture
    async def psycopg3_async_connection(self, psycopg3_connection_string):
        """Create a psycopg3 async connection to the test database."""
        try:
            import psycopg
        except ImportError:
            pytest.skip("psycopg (version 3) not installed")

        conn = await psycopg.AsyncConnection.connect(psycopg3_connection_string)

        # Create the users table
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS tests_user (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    age INTEGER,
                    email VARCHAR(100) NOT NULL,
                    username VARCHAR(100) NOT NULL,
                    address TEXT
                )
            """)
            await conn.commit()

        yield conn

        # Cleanup
        await conn.close()

    @pytest.mark.asyncio
    async def test_async_connection_detection(self, psycopg3_async_connection):
        """Test that psycopg3 async connection is detected correctly."""
        from src.djazzle.connection import ConnectionAdapter

        adapter = ConnectionAdapter(psycopg3_async_connection)
        assert adapter.conn_type == 'psycopg3_async'
        assert adapter.is_async is True

    @pytest.mark.asyncio
    async def test_async_select_query(self, psycopg3_async_connection, users_table):
        """Test async SELECT query with psycopg3."""
        # Insert test data using raw psycopg3 async
        async with psycopg3_async_connection.cursor() as cur:
            await cur.execute(
                "INSERT INTO tests_user (name, age, email, username, address) VALUES (%s, %s, %s, %s, %s)",
                ("AsyncAlice", 30, "async.alice@example.com", "async_alice", "123 Async St")
            )
            await psycopg3_async_connection.commit()

        # Query using Djazzle with custom async connection
        db = DjazzleQuery(conn=psycopg3_async_connection)
        results = await db.select("name", "age").from_(users_table).where(eq(users_table.name, "AsyncAlice"))

        assert len(results) == 1
        assert results[0]["name"] == "AsyncAlice"
        assert results[0]["age"] == 30

    @pytest.mark.asyncio
    async def test_async_insert_query(self, psycopg3_async_connection, users_table):
        """Test async INSERT query with psycopg3."""
        db = DjazzleQuery(conn=psycopg3_async_connection)

        # Insert using Djazzle async
        await db.insert(users_table).values({
            "name": "AsyncBob",
            "age": 25,
            "email": "async.bob@example.com",
            "username": "async_bob",
            "address": "456 Async St"
        })

        # Verify using raw psycopg3
        async with psycopg3_async_connection.cursor() as cur:
            await cur.execute("SELECT name, age FROM tests_user WHERE name = %s", ("AsyncBob",))
            row = await cur.fetchone()
            assert row[0] == "AsyncBob"
            assert row[1] == 25

    @pytest.mark.asyncio
    async def test_async_insert_with_returning(self, psycopg3_async_connection, users_table):
        """Test async INSERT with RETURNING clause."""
        db = DjazzleQuery(conn=psycopg3_async_connection)

        # Insert with RETURNING
        results = await db.insert(users_table).values({
            "name": "AsyncCharlie",
            "age": 35,
            "email": "async.charlie@example.com",
            "username": "async_charlie",
            "address": "789 Async St"
        }).returning()

        assert len(results) == 1
        assert results[0]["name"] == "AsyncCharlie"
        assert results[0]["age"] == 35
        assert results[0]["id"] is not None

    @pytest.mark.asyncio
    async def test_async_update_query(self, psycopg3_async_connection, users_table):
        """Test async UPDATE query with psycopg3."""
        # Insert test data
        async with psycopg3_async_connection.cursor() as cur:
            await cur.execute(
                "INSERT INTO tests_user (name, age, email, username, address) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                ("AsyncDave", 40, "async.dave@example.com", "async_dave", "111 Async St")
            )
            user_id = (await cur.fetchone())[0]
            await psycopg3_async_connection.commit()

        # Update using Djazzle async
        db = DjazzleQuery(conn=psycopg3_async_connection)
        await db.update(users_table).set({"age": 41}).where(eq(users_table.id, user_id))

        # Verify
        async with psycopg3_async_connection.cursor() as cur:
            await cur.execute("SELECT age FROM tests_user WHERE id = %s", (user_id,))
            age = (await cur.fetchone())[0]
            assert age == 41

    @pytest.mark.asyncio
    async def test_async_delete_query(self, psycopg3_async_connection, users_table):
        """Test async DELETE query with psycopg3."""
        # Insert test data
        async with psycopg3_async_connection.cursor() as cur:
            await cur.execute(
                "INSERT INTO tests_user (name, age, email, username, address) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                ("AsyncEve", 45, "async.eve@example.com", "async_eve", "222 Async St")
            )
            user_id = (await cur.fetchone())[0]
            await psycopg3_async_connection.commit()

        # Delete using Djazzle async
        db = DjazzleQuery(conn=psycopg3_async_connection)
        await db.delete(users_table).where(eq(users_table.id, user_id))

        # Verify
        async with psycopg3_async_connection.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM tests_user WHERE id = %s", (user_id,))
            count = (await cur.fetchone())[0]
            assert count == 0

    @pytest.mark.asyncio
    async def test_async_bulk_insert(self, psycopg3_async_connection, users_table):
        """Test async bulk INSERT with psycopg3."""
        db = DjazzleQuery(conn=psycopg3_async_connection)

        # Bulk insert
        await db.insert(users_table).values([
            {
                "name": f"AsyncUser{i}",
                "age": 20 + i,
                "email": f"async.user{i}@example.com",
                "username": f"async_user{i}",
                "address": f"{i} Async User St"
            }
            for i in range(5)
        ])

        # Verify
        results = await db.select().from_(users_table)
        user_names = [r["name"] for r in results if r["name"].startswith("AsyncUser")]
        assert len(user_names) >= 5

    @pytest.mark.asyncio
    async def test_cannot_use_sync_call_with_async_connection(self, psycopg3_async_connection, users_table):
        """Test that sync () call raises error with async connection."""
        db = DjazzleQuery(conn=psycopg3_async_connection)

        # Attempting to use sync call should raise an error
        with pytest.raises(RuntimeError, match="Cannot use synchronous execute"):
            db.select().from_(users_table)()
