"""Tests for async query execution."""

import pytest
from src.djazzle import eq
from tests.models import User


@pytest.mark.django_db(transaction=True)
class TestAsyncQueries:
    """Test async query execution support."""

    @pytest.fixture
    def async_users(self):
        """Create sample async test users."""
        User.objects.create(
            name="AsyncUser1",
            age=25,
            email="async1@example.com",
            username="async1",
            address="123 Async St"
        )
        User.objects.create(
            name="AsyncUser2",
            age=30,
            email="async2@example.com",
            username="async2",
            address="456 Async Ave"
        )
        yield

    @pytest.mark.asyncio
    async def test_async_select_query(self, db, users_table, async_users):
        """Test async SELECT queries using await syntax."""
        rows = await db.select("id", "name", "age").from_(users_table).where(eq(users_table.name, "AsyncUser1"))

        assert len(rows) == 1
        assert rows[0]["name"] == "AsyncUser1"
        assert rows[0]["age"] == 25

    @pytest.mark.asyncio
    async def test_async_select_all(self, db, users_table, async_users):
        """Test async SELECT * query."""
        rows = await db.select().from_(users_table)

        # Should have at least our 2 test users
        async_users_found = [r for r in rows if r["name"].startswith("AsyncUser")]
        assert len(async_users_found) >= 2

    @pytest.mark.asyncio
    async def test_async_select_as_model(self, db, users_table, async_users):
        """Test async SELECT returning model instances."""
        rows = await db.select().from_(users_table).where(eq(users_table.name, "AsyncUser2")).as_model()

        assert len(rows) == 1
        user = rows[0]
        assert isinstance(user, User)
        assert user.name == "AsyncUser2"
        assert user.age == 30

    @pytest.mark.asyncio
    async def test_async_insert(self, db, users_table):
        """Test async INSERT query."""
        result = await db.insert(users_table).values({
            "name": "AsyncInsert",
            "age": 35,
            "email": "asyncinsert@example.com",
            "username": "async_insert",
            "address": "789 Insert Ln"
        })

        assert result is None

        # Verify it was inserted
        rows = await db.select().from_(users_table).where(eq(users_table.name, "AsyncInsert"))
        assert len(rows) == 1
        assert rows[0]["name"] == "AsyncInsert"
        assert rows[0]["age"] == 35

    @pytest.mark.asyncio
    async def test_async_insert_with_returning(self, db, users_table):
        """Test async INSERT with RETURNING clause."""
        from django.db import connection
        if connection.vendor != "postgresql":
            pytest.skip("RETURNING is only supported in PostgreSQL")

        result = await db.insert(users_table).values({
            "name": "AsyncReturn",
            "age": 40,
            "email": "asyncreturn@example.com",
            "username": "async_return",
            "address": "321 Return Rd"
        }).returning()

        assert len(result) == 1
        assert result[0]["name"] == "AsyncReturn"
        assert result[0]["age"] == 40
        assert result[0]["id"] is not None

    @pytest.mark.asyncio
    async def test_async_update(self, db, users_table):
        """Test async UPDATE query."""
        # Create a user to update using Django ORM async
        user = await User.objects.acreate(
            name="AsyncUpdateTest",
            age=20,
            email="asyncupdate@example.com",
            username="async_update",
            address="111 Update St"
        )

        # Update using Djazzle
        result = await db.update(users_table).set({"age": 21}).where(eq(users_table.id, user.id))
        assert result is None

        # Verify the update
        rows = await db.select().from_(users_table).where(eq(users_table.id, user.id))
        assert len(rows) == 1
        assert rows[0]["age"] == 21

        # Clean up
        await user.adelete()

    @pytest.mark.asyncio
    async def test_async_update_with_returning(self, db, users_table):
        """Test async UPDATE with RETURNING clause."""
        from django.db import connection
        if connection.vendor != "postgresql":
            pytest.skip("RETURNING is only supported in PostgreSQL")

        # Create a user to update
        user = await User.objects.acreate(
            name="AsyncUpdateReturn",
            age=50,
            email="asyncupdatereturn@example.com",
            username="async_update_return",
            address="222 Update Ave"
        )

        # Update with returning
        result = await db.update(users_table).set({"age": 51}).where(
            eq(users_table.id, user.id)
        ).returning()

        assert len(result) == 1
        assert result[0]["age"] == 51
        assert result[0]["id"] == user.id

        # Clean up
        await user.adelete()

    @pytest.mark.asyncio
    async def test_async_delete(self, db, users_table):
        """Test async DELETE query."""
        # Create a user to delete
        user = await User.objects.acreate(
            name="AsyncDeleteTest",
            age=60,
            email="asyncdelete@example.com",
            username="async_delete",
            address="333 Delete Blvd"
        )

        # Delete using Djazzle
        result = await db.delete(users_table).where(eq(users_table.id, user.id))
        assert result is None

        # Verify it was deleted
        rows = await db.select().from_(users_table).where(eq(users_table.id, user.id))
        assert len(rows) == 0

    @pytest.mark.asyncio
    async def test_async_bulk_insert(self, db, users_table):
        """Test async bulk INSERT."""
        values = [
            {
                "name": f"AsyncBulk{i}",
                "age": 20 + i,
                "email": f"asyncbulk{i}@example.com",
                "username": f"async_bulk_{i}",
                "address": f"{i} Bulk St"
            }
            for i in range(5)
        ]

        result = await db.insert(users_table).values(values)
        assert result is None

        # Verify they were inserted
        rows = await db.select().from_(users_table)
        bulk_users = [r for r in rows if r["name"].startswith("AsyncBulk")]
        assert len(bulk_users) == 5

        # Clean up
        await User.objects.filter(name__startswith="AsyncBulk").adelete()
