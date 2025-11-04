"""Tests for INSERT queries."""

import pytest
from unittest import skipIf
from django.db import connection
from src.djazzle import eq
from tests.models import User


@pytest.mark.django_db
class TestInsert:
    """Tests for INSERT queries."""

    def test_insert_single_row(self, db, users_table):
        """Test inserting a single row without RETURNING."""
        result = db.insert(users_table).values({
            "name": "Charlie",
            "age": 25,
            "email": "charlie@example.com",
            "username": "charlie",
            "address": "123 Main St"
        })()
        assert result is None

        # Verify it was inserted
        rows = db.select().from_(users_table).where(eq(users_table.name, "Charlie"))()
        assert len(rows) == 1
        assert rows[0]["name"] == "Charlie"
        assert rows[0]["age"] == 25

    @skipIf(
        connection.vendor != "postgresql",
        "RETURNING is only supported in PostgreSQL"
    )
    def test_insert_with_returning(self, db, users_table):
        """Test INSERT with RETURNING clause (PostgreSQL only)."""
        result = db.insert(users_table).values({
            "name": "Diana",
            "age": 28,
            "email": "diana@example.com",
            "username": "diana",
            "address": "456 Elm St"
        }).returning()()

        assert len(result) == 1
        assert result[0]["name"] == "Diana"
        assert result[0]["age"] == 28
        assert result[0]["id"] is not None

    @skipIf(
        connection.vendor != "postgresql",
        "RETURNING is only supported in PostgreSQL"
    )
    def test_insert_with_returning_specific_fields(self, db, users_table):
        """Test INSERT with RETURNING specific fields (PostgreSQL only)."""
        result = db.insert(users_table).values({
            "name": "Eve",
            "age": 32,
            "email": "eve@example.com",
            "username": "eve",
            "address": "789 Oak Ave"
        }).returning("id", "name")()

        assert len(result) == 1
        assert "id" in result[0]
        assert "name" in result[0]
        assert result[0]["name"] == "Eve"
        # age should not be in the result
        assert "age" not in result[0]

    def test_insert_multiple_rows(self, db, users_table):
        """Test bulk insert of multiple rows."""
        result = db.insert(users_table).values([
            {
                "name": "User1",
                "age": 20,
                "email": "user1@example.com",
                "username": "user1",
                "address": "111 First St"
            },
            {
                "name": "User2",
                "age": 21,
                "email": "user2@example.com",
                "username": "user2",
                "address": "222 Second St"
            },
            {
                "name": "User3",
                "age": 22,
                "email": "user3@example.com",
                "username": "user3",
                "address": "333 Third St"
            }
        ])()

        assert result is None

        # Verify all were inserted
        rows = db.select().from_(users_table)()
        user_names = {row["name"] for row in rows}
        assert "User1" in user_names
        assert "User2" in user_names
        assert "User3" in user_names

    def test_insert_sql_generation(self, db, users_table):
        """Test that INSERT SQL is generated correctly."""
        query = db.insert(users_table).values({
            "name": "Test",
            "age": 25,
            "email": "test@example.com",
            "username": "test",
            "address": "123 Test St"
        })

        sql = query.sql
        params = query.params

        assert "INSERT INTO" in sql
        assert '"users"' in sql.lower() or '"tests_user"' in sql.lower()
        assert "name" in sql
        assert "age" in sql
        assert "Test" in params
        assert 25 in params

    def test_invalid_type_raises(self, db, users_table):
        """Test that setting a column to an invalid type raises TypeError."""
        # Attempt to set age (IntegerField) to a string
        with pytest.raises(TypeError) as exc_info:
            db.insert(users_table).values({
            "name": "Test",
            "age": "not-an-integer",
            "email": "test@example.com",
            "username": "test",
            "address": "123 Test St"
        })

        # Optional: check that the error message contains expected info
        assert "Invalid type for column 'age'" in str(exc_info.value)
        assert "expected int" in str(exc_info.value) or "got str" in str(exc_info.value)
