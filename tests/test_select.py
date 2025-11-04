"""Tests for SELECT queries."""

import pytest
from src.djazzle import eq
from tests.models import User, Pet


@pytest.mark.django_db
class TestBasicSelect:
    """Tests for basic SELECT queries."""

    def test_column_access(self, users_table):
        """Test that table columns are accessible as attributes."""
        assert hasattr(users_table, "id")
        assert hasattr(users_table, "name")
        assert hasattr(users_table, "age")

    def test_simple_query(self, db, users_table, sample_users):
        """Test a simple SELECT query with WHERE clause."""
        rows = db.select("id", "name", "age").from_(users_table).where(eq(users_table.name, "Alice"))()
        assert len(rows) == 1
        assert rows[0]["name"] == "Alice"

    def test_model_return(self, db, users_table, sample_users):
        """Test SELECT query returning Django model instances."""
        rows = db.select("id", "name").from_(users_table).where(eq(users_table.name, "Bob")).as_model()()
        assert len(rows) == 1
        user = rows[0]
        assert isinstance(user, User)
        assert user.name == "Bob"
        assert user.age is None


@pytest.mark.django_db
class TestSelectAliases:
    """Tests for SELECT queries with column aliases."""

    def test_select_with_alias(self, db, users_table, sample_users):
        """Test SELECT with simple alias."""
        query = db.select("id as user_id", "name").from_(users_table)
        sql = query.sql

        assert '"id" AS "user_id"' in sql
        assert '"name"' in sql

    def test_select_multiple_aliases(self, db, users_table, sample_users):
        """Test SELECT with multiple aliases."""
        query = db.select("id as user_id", "name as user_name", "age as user_age").from_(users_table)
        sql = query.sql

        assert '"id" AS "user_id"' in sql
        assert '"name" AS "user_name"' in sql
        assert '"age" AS "user_age"' in sql

    def test_select_qualified_name_with_alias(self, db, users_table, sample_users):
        """Test SELECT with qualified column names and aliases."""
        query = db.select("users.id as user_id", "users.name").from_(users_table)
        sql = query.sql

        assert '"users"."id" AS "user_id"' in sql
        assert '"users"."name"' in sql

    def test_select_alias_case_insensitive(self, db, users_table, sample_users):
        """Test that AS keyword is case insensitive."""
        query = db.select("id AS user_id", "name As user_name").from_(users_table)
        sql = query.sql

        assert '"id" AS "user_id"' in sql
        assert '"name" AS "user_name"' in sql

    def test_select_with_column_object(self, db, users_table, sample_users):
        """Test SELECT using Column objects."""
        query = db.select(users_table.id, users_table.name).from_(users_table)
        sql = query.sql

        assert '"id"' in sql
        assert '"name"' in sql

    def test_select_with_alias_method(self, db, users_table, sample_users):
        """Test SELECT using Column.as_() method."""
        query = db.select(users_table.id.as_("user_id"), users_table.name).from_(users_table)
        sql = query.sql

        assert '"id" AS "user_id"' in sql
        assert '"name"' in sql

    def test_select_mixed_columns_and_strings(self, db, users_table, sample_users):
        """Test SELECT mixing Column objects and string field names."""
        query = db.select(users_table.id, "name", users_table.age.as_("user_age")).from_(users_table)
        sql = query.sql

        assert '"id"' in sql
        assert '"name"' in sql
        assert '"age" AS "user_age"' in sql


@pytest.mark.django_db
class TestJoins:
    """Tests for JOIN queries."""

    @pytest.fixture
    def sample_data_with_pets(self):
        """Create sample users and pets for join testing."""
        alice = User.objects.create(
            name="Alice",
            age=30,
            email="alice@example.com",
            username="alice",
            address="123 Alice St"
        )
        Pet.objects.create(
            name="Fluffy",
            species="cat",
            owner=alice
        )
        yield
        # Cleanup happens automatically

    def test_left_join_sql_generation(self, db, users_table, pets_table, sample_data_with_pets):
        """Test LEFT JOIN SQL generation."""
        query = db.select().from_(users_table).left_join(pets_table, eq(users_table.id, pets_table.owner_id))
        sql = query.sql

        assert "LEFT JOIN" in sql
        assert pets_table.db_table_name in sql

    def test_inner_join_sql_generation(self, db, users_table, pets_table, sample_data_with_pets):
        """Test INNER JOIN SQL generation."""
        query = db.select().from_(users_table).inner_join(pets_table, eq(users_table.id, pets_table.owner_id))
        sql = query.sql

        assert "INNER JOIN" in sql
        assert pets_table.db_table_name in sql

    def test_right_join_sql_generation(self, db, users_table, pets_table, sample_data_with_pets):
        """Test RIGHT JOIN SQL generation."""
        query = db.select().from_(users_table).right_join(pets_table, eq(users_table.id, pets_table.owner_id))
        sql = query.sql

        assert "RIGHT JOIN" in sql
        assert pets_table.db_table_name in sql

    def test_full_join_sql_generation(self, db, users_table, pets_table, sample_data_with_pets):
        """Test FULL JOIN SQL generation."""
        query = db.select().from_(users_table).full_join(pets_table, eq(users_table.id, pets_table.owner_id))
        sql = query.sql

        assert "FULL JOIN" in sql
        assert pets_table.db_table_name in sql

    def test_join_with_where_clause(self, db, users_table, pets_table, sample_data_with_pets):
        """Test JOIN with WHERE clause."""
        query = db.select().from_(users_table).left_join(
            pets_table, eq(users_table.id, pets_table.owner_id)
        ).where(eq(users_table.age, 25))
        sql = query.sql

        assert "LEFT JOIN" in sql
        assert "WHERE" in sql

    def test_join_with_partial_select(self, db, users_table, pets_table, sample_data_with_pets):
        """Test JOIN with partial column selection."""
        query = db.select("users.id", "users.name", "pets.name").from_(users_table).left_join(
            pets_table, eq(users_table.id, pets_table.owner_id)
        )
        sql = query.sql

        assert '"users"."id"' in sql
        assert '"users"."name"' in sql
        assert '"pets"."name"' in sql

    def test_multiple_joins(self, db, users_table, pets_table, sample_data_with_pets):
        """Test multiple JOIN clauses."""
        from src.djazzle import TableFromModel
        # Just test SQL generation for multiple joins
        query = db.select().from_(users_table).left_join(
            pets_table, eq(users_table.id, pets_table.owner_id)
        ).inner_join(
            users_table, eq(pets_table.owner_id, users_table.id)
        )
        sql = query.sql

        assert sql.count("JOIN") == 2

    def test_select_column_with_join(self, db, users_table, pets_table, sample_data_with_pets):
        """Test Column objects in JOIN queries."""
        query = db.select(users_table.name, pets_table.name.as_("pet_name")).from_(users_table).left_join(
            pets_table, eq(users_table.id, pets_table.owner_id)
        )
        sql = query.sql

        assert '"name"' in sql
        assert '"name" AS "pet_name"' in sql
        assert "LEFT JOIN" in sql
