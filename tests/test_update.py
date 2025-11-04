"""Tests for UPDATE queries."""

import pytest
from unittest import skipIf
from django.db import connection
from src.djazzle import eq
from tests.models import User


@pytest.mark.django_db
class TestUpdate:
    """Tests for UPDATE queries."""

    @pytest.fixture
    def test_user(self):
        """Create a test user for update operations."""
        user = User.objects.create(
            name="UpdateTest",
            age=25,
            email="update@example.com",
            username="updatetest",
            address="123 Update St"
        )
        return user

    def test_update_basic(self, db, users_table, test_user):
        """Test basic UPDATE query."""
        result = db.update(users_table).set({"age": 26}).where(eq(users_table.id, test_user.id))()
        assert result is None

        # Verify the update
        rows = db.select().from_(users_table).where(eq(users_table.id, test_user.id))()
        assert len(rows) == 1
        assert rows[0]["age"] == 26

    @skipIf(
        connection.vendor != "postgresql",
        "RETURNING is only supported in PostgreSQL"
    )
    def test_update_with_returning(self, db, users_table, test_user):
        """Test UPDATE with RETURNING clause (PostgreSQL only)."""
        result = db.update(users_table).set({"age": 27}).where(
            eq(users_table.id, test_user.id)
        ).returning()()

        assert len(result) == 1
        assert result[0]["age"] == 27
        assert result[0]["id"] == test_user.id

    @skipIf(
        connection.vendor != "postgresql",
        "RETURNING is only supported in PostgreSQL"
    )
    def test_update_with_returning_specific_fields(self, db, users_table, test_user):
        """Test UPDATE with RETURNING specific fields (PostgreSQL only)."""
        result = db.update(users_table).set({"age": 28}).where(
            eq(users_table.id, test_user.id)
        ).returning("id", "age")()

        assert len(result) == 1
        assert "id" in result[0]
        assert "age" in result[0]
        assert result[0]["age"] == 28
        # name should not be in the result
        assert "name" not in result[0]

    def test_update_multiple_fields(self, db, users_table, test_user):
        """Test updating multiple fields at once."""
        result = db.update(users_table).set({
            "name": "UpdatedName",
            "age": 30
        }).where(eq(users_table.id, test_user.id))()

        assert result is None

        # Verify the updates
        rows = db.select().from_(users_table).where(eq(users_table.id, test_user.id))()
        assert len(rows) == 1
        assert rows[0]["name"] == "UpdatedName"
        assert rows[0]["age"] == 30

    def test_update_set_null(self, db, users_table, test_user):
        """Test setting a field to NULL."""
        result = db.update(users_table).set({"age": None}).where(eq(users_table.id, test_user.id))()
        assert result is None

        # Verify age is now NULL
        rows = db.select().from_(users_table).where(eq(users_table.id, test_user.id))()
        assert len(rows) == 1
        assert rows[0]["age"] is None

    def test_update_sql_generation(self, db, users_table, test_user):
        """Test that UPDATE SQL is generated correctly."""
        query = db.update(users_table).set({"age": 35}).where(eq(users_table.id, test_user.id))

        sql = query.sql
        params = query.params

        assert "UPDATE" in sql
        assert '"users"' in sql.lower() or '"tests_user"' in sql.lower()
        assert "SET" in sql
        assert "age" in sql
        assert "WHERE" in sql
        assert 35 in params
        assert test_user.id in params
