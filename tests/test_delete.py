"""Tests for DELETE queries."""

import pytest
from unittest import skipIf
from django.db import connection
from src.djazzle import eq, and_, lt
from tests.models import User


@pytest.mark.django_db
class TestDelete:
    """Tests for DELETE queries."""

    @pytest.fixture
    def test_users(self):
        """Create test users for delete operations."""
        users = [
            User.objects.create(
                name=f"DeleteTest{i}",
                age=20 + i,
                email=f"delete{i}@example.com",
                username=f"deletetest{i}",
                address=f"{i} Delete St"
            )
            for i in range(3)
        ]
        return users

    def test_delete_basic(self, db, users_table, test_users):
        """Test basic DELETE query."""
        user_to_delete = test_users[0]
        result = db.delete(users_table).where(eq(users_table.id, user_to_delete.id))()
        assert result is None

        # Verify it was deleted
        rows = db.select().from_(users_table).where(eq(users_table.id, user_to_delete.id))()
        assert len(rows) == 0

    @skipIf(
        connection.vendor != "postgresql",
        "RETURNING is only supported in PostgreSQL"
    )
    def test_delete_with_returning(self, db, users_table, test_users):
        """Test DELETE with RETURNING clause (PostgreSQL only)."""
        user_to_delete = test_users[0]
        result = db.delete(users_table).where(eq(users_table.id, user_to_delete.id)).returning()()

        assert len(result) == 1
        assert result[0]["id"] == user_to_delete.id
        assert result[0]["name"] == user_to_delete.name

        # Verify it was deleted
        rows = db.select().from_(users_table).where(eq(users_table.id, user_to_delete.id))()
        assert len(rows) == 0

    @skipIf(
        connection.vendor != "postgresql",
        "RETURNING is only supported in PostgreSQL"
    )
    def test_delete_with_returning_specific_fields(self, db, users_table, test_users):
        """Test DELETE with RETURNING specific fields (PostgreSQL only)."""
        user_to_delete = test_users[0]
        result = db.delete(users_table).where(
            eq(users_table.id, user_to_delete.id)
        ).returning("id", "name")()

        assert len(result) == 1
        assert "id" in result[0]
        assert "name" in result[0]
        # age should not be in the result
        assert "age" not in result[0]

    @skipIf(
        connection.vendor == "sqlite",
        "SQLite doesn't support LIMIT in DELETE without ORDER BY"
    )
    def test_delete_with_limit(self, db, users_table, test_users):
        """Test DELETE with LIMIT clause."""
        # Delete only the first user that matches
        initial_count = len(db.select().from_(users_table)())

        result = db.delete(users_table).where(eq(users_table.age, 20)).limit(1)()
        assert result is None

        # Verify only one was deleted
        final_count = len(db.select().from_(users_table)())
        assert final_count == initial_count - 1

    def test_delete_sql_generation(self, db, users_table, test_users):
        """Test that DELETE SQL is generated correctly."""
        user = test_users[0]
        query = db.delete(users_table).where(eq(users_table.id, user.id))

        sql = query.sql
        params = query.params

        assert "DELETE FROM" in sql
        assert '"users"' in sql.lower() or '"tests_user"' in sql.lower()
        assert "WHERE" in sql
        assert user.id in params
