from typing import reveal_type, Any, TYPE_CHECKING, List, TypedDict
from unittest import skipIf

from django.db import connection
from django.test import TestCase
from .models import User, Pet
from src.djazzle import TableFromModel, DjazzleQuery, eq

# Manual TypedDict for IDE support
class UserRow(TypedDict):
    id: int
    name: str
    age: int | None

class DjazzleTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
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

    def test_column_access(self):
        users = TableFromModel(User)
        self.assertTrue(hasattr(users, "id"))
        self.assertTrue(hasattr(users, "name"))
        self.assertTrue(hasattr(users, "age"))

    def test_simple_query(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        rows = db.select("id", "name", "age").from_(users).where(eq(users.name, "Alice"))()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Alice")

    def test_model_return(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        rows = db.select("id", "name").from_(users).where(eq(users.name, "Bob")).as_model()()
        self.assertEqual(len(rows), 1)
        user = rows[0]
        self.assertEqual(user.name, "Bob")
        self.assertIsNone(user.age)

    def test_insert_single_row(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Insert without returning
        result = db.insert(users).values({
            "name": "Charlie",
            "age": 25,
            "email": "charlie@example.com",
            "username": "charlie",
            "address": "123 Main St"
        })()
        self.assertIsNone(result)

        # Verify it was inserted
        rows = db.select().from_(users).where(eq(users.name, "Charlie"))()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Charlie")
        self.assertEqual(rows[0]["age"], 25)

    def test_insert_with_returning(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Insert with returning all fields
        result = db.insert(users).values({
            "name": "Diana",
            "age": 28,
            "email": "diana@example.com",
            "username": "diana",
            "address": "456 Elm St"
        }).returning()()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Diana")
        self.assertEqual(result[0]["age"], 28)
        self.assertIsNotNone(result[0]["id"])

    def test_insert_with_returning_specific_fields(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Insert with returning specific fields
        result = db.insert(users).values({
            "name": "Eve",
            "age": 32,
            "email": "eve@example.com",
            "username": "eve",
            "address": "789 Oak St"
        }).returning("id", "name")()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Eve")
        self.assertIsNotNone(result[0]["id"])
        self.assertNotIn("age", result[0])

    def test_insert_multiple_rows(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Insert multiple rows with returning
        result = db.insert(users).values([
            {
                "name": "Frank",
                "age": 35,
                "email": "frank@example.com",
                "username": "frank",
                "address": "111 Pine St"
            },
            {
                "name": "Grace",
                "age": 40,
                "email": "grace@example.com",
                "username": "grace",
                "address": "222 Maple St"
            }
        ]).returning()()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Frank")
        self.assertEqual(result[0]["age"], 35)
        self.assertEqual(result[1]["name"], "Grace")
        self.assertEqual(result[1]["age"], 40)

    def test_insert_sql_generation(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Test SQL generation without executing
        query = db.insert(users).values({
            "name": "Henry",
            "age": 45,
            "email": "henry@example.com",
            "username": "henry",
            "address": "333 Birch St"
        })
        sql = query.sql
        params = query.params

        self.assertIn("INSERT INTO", sql)
        self.assertIn('"name"', sql)
        self.assertIn('"age"', sql)
        # Params should be in the same order as the dict keys (insertion order)
        self.assertEqual(params, ["Henry", 45, "henry@example.com", "henry", "333 Birch St"])

    def test_update_basic(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Update without returning
        result = db.update(users).set({"name": "Mr. Bob"}).where(eq(users.name, "Bob"))()
        self.assertIsNone(result)

        # Verify it was updated
        rows = db.select().from_(users).where(eq(users.name, "Mr. Bob"))()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Mr. Bob")

    def test_update_with_returning(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Update with returning
        result = db.update(users).set({"age": 35}).where(eq(users.name, "Alice")).returning()()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Alice")
        self.assertEqual(result[0]["age"], 35)

    def test_update_with_returning_specific_fields(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Update with returning specific fields
        result = db.update(users).set({"age": 40}).where(eq(users.name, "Alice")).returning("id", "age")()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["age"], 40)
        self.assertIsNotNone(result[0]["id"])
        self.assertNotIn("name", result[0])

    def test_update_multiple_fields(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Update multiple fields
        result = db.update(users).set({
            "name": "Alice Smith",
            "age": 31
        }).where(eq(users.name, "Alice")).returning()()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Alice Smith")
        self.assertEqual(result[0]["age"], 31)

    def test_update_set_null(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Set a field to NULL
        result = db.update(users).set({"age": None}).where(eq(users.name, "Alice")).returning()()
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["age"])

    def test_update_sql_generation(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Test SQL generation without executing
        query = db.update(users).set({"name": "Mr. Bob", "age": 50}).where(eq(users.id, 1))
        sql = query.sql
        params = query.params

        self.assertIn("UPDATE", sql)
        self.assertIn("SET", sql)
        self.assertIn('"name"', sql)
        self.assertIn('"age"', sql)
        self.assertIn("WHERE", sql)
        # First two params are from SET, last is from WHERE
        self.assertEqual(params[:2], ["Mr. Bob", 50])
        self.assertEqual(params[2], 1)

    def test_delete_basic(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Delete with WHERE clause
        result = db.delete(users).where(eq(users.name, "Bob"))()
        self.assertIsNone(result)

        # Verify it was deleted
        rows = db.select().from_(users).where(eq(users.name, "Bob"))()
        self.assertEqual(len(rows), 0)

    def test_delete_with_returning(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Delete with returning
        result = db.delete(users).where(eq(users.name, "Alice")).returning()()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Alice")
        self.assertEqual(result[0]["age"], 30)

        # Verify it was deleted
        rows = db.select().from_(users).where(eq(users.name, "Alice"))()
        self.assertEqual(len(rows), 0)

    def test_delete_with_returning_specific_fields(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # First, insert a new user to delete
        db.insert(users).values({
            "name": "ToDelete",
            "age": 99,
            "email": "delete@example.com",
            "username": "todelete",
            "address": "Delete St"
        })()

        # Delete with returning specific fields
        result = db.delete(users).where(eq(users.name, "ToDelete")).returning("id", "name")()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "ToDelete")
        self.assertIsNotNone(result[0]["id"])
        self.assertNotIn("age", result[0])

    @skipIf(connection.vendor == "sqlite", "SQLite doesn't support DELETE ... LIMIT")
    def test_delete_with_limit(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Insert multiple users with same name
        db.insert(users).values([
            {"name": "Multi", "age": 20, "email": "m1@example.com", "username": "m1", "address": "M1 St"},
            {"name": "Multi", "age": 21, "email": "m2@example.com", "username": "m2", "address": "M2 St"},
            {"name": "Multi", "age": 22, "email": "m3@example.com", "username": "m3", "address": "M3 St"},
        ])()

        # Delete only 2 rows
        query = db.delete(users).where(eq(users.name, "Multi")).limit(2)
        print(query.sql)
        query()

        # Verify only 2 were deleted (1 should remain)
        rows = db.select().from_(users).where(eq(users.name, "Multi"))()
        self.assertEqual(len(rows), 1)

    def test_delete_sql_generation(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Test SQL generation without executing
        query = db.delete(users).where(eq(users.name, "Dan"))
        sql = query.sql
        params = query.params

        self.assertIn("DELETE FROM", sql)
        self.assertIn("WHERE", sql)
        self.assertEqual(params, ["Dan"])

    def test_left_join_sql_generation(self):
        users = TableFromModel(User)
        pets = TableFromModel(Pet)
        db = DjazzleQuery()

        # Test LEFT JOIN SQL generation
        # pets.owner_id should now be available thanks to table.py updates
        query = db.select().from_(users).left_join(pets, eq(users.id, pets.owner_id))
        sql = query.sql

        self.assertIn("SELECT * FROM", sql)
        self.assertIn("LEFT JOIN", sql)
        self.assertIn('"tests_pet"', sql)
        self.assertIn("ON", sql)

    def test_inner_join_sql_generation(self):
        users = TableFromModel(User)
        pets = TableFromModel(Pet)
        db = DjazzleQuery()

        # Test INNER JOIN SQL generation
        query = db.select().from_(users).inner_join(pets, eq(users.id, pets.owner_id))
        sql = query.sql

        self.assertIn("INNER JOIN", sql)
        self.assertIn('"tests_pet"', sql)

    def test_right_join_sql_generation(self):
        users = TableFromModel(User)
        pets = TableFromModel(Pet)
        db = DjazzleQuery()

        # Test RIGHT JOIN SQL generation
        query = db.select().from_(users).right_join(pets, eq(users.id, pets.owner_id))
        sql = query.sql

        self.assertIn("RIGHT JOIN", sql)
        self.assertIn('"tests_pet"', sql)

    def test_full_join_sql_generation(self):
        users = TableFromModel(User)
        pets = TableFromModel(Pet)
        db = DjazzleQuery()

        # Test FULL JOIN SQL generation
        query = db.select().from_(users).full_join(pets, eq(users.id, pets.owner_id))
        sql = query.sql

        self.assertIn("FULL JOIN", sql)
        self.assertIn('"tests_pet"', sql)

    def test_join_with_where_clause(self):
        users = TableFromModel(User)
        pets = TableFromModel(Pet)
        db = DjazzleQuery()

        # Test JOIN with WHERE clause
        query = db.select().from_(users).left_join(pets, eq(users.id, pets.owner_id)).where(eq(users.age, 25))
        sql = query.sql
        params = query.params

        self.assertIn("LEFT JOIN", sql)
        self.assertIn("WHERE", sql)
        self.assertEqual(params, [25])

    def test_join_with_partial_select(self):
        users = TableFromModel(User)
        pets = TableFromModel(Pet)
        db = DjazzleQuery()

        # Test partial select with qualified column names
        query = db.select("tests_user.id", "tests_user.name", "tests_pet.id", "tests_pet.name").from_(users).left_join(pets, eq(users.id, pets.owner_id))
        sql = query.sql

        self.assertIn('"tests_user"."id"', sql)
        self.assertIn('"tests_user"."name"', sql)
        self.assertIn('"tests_pet"."id"', sql)
        self.assertIn('"tests_pet"."name"', sql)
        self.assertIn("LEFT JOIN", sql)

    def test_multiple_joins(self):
        users = TableFromModel(User)
        pets = TableFromModel(Pet)
        db = DjazzleQuery()

        # Test multiple JOINs
        query = db.select().from_(users).left_join(pets, eq(users.id, pets.owner_id)).inner_join(pets, eq(users.id, pets.owner_id))
        sql = query.sql

        # Should have two JOIN clauses
        self.assertEqual(sql.count("JOIN"), 2)
        self.assertIn("LEFT JOIN", sql)
        self.assertIn("INNER JOIN", sql)

    def test_select_with_alias(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Test simple alias
        query = db.select("name as my_name").from_(users)
        sql = query.sql

        self.assertIn('"name" AS "my_name"', sql)

    def test_select_multiple_aliases(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Test multiple aliases
        query = db.select("id as user_id", "name as user_name", "age").from_(users)
        sql = query.sql

        self.assertIn('"id" AS "user_id"', sql)
        self.assertIn('"name" AS "user_name"', sql)
        self.assertIn('"age"', sql)

    def test_select_qualified_name_with_alias(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Test qualified column name with alias
        query = db.select("tests_user.name as full_name").from_(users)
        sql = query.sql

        self.assertIn('"tests_user"."name" AS "full_name"', sql)

    def test_select_alias_case_insensitive(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Test that 'AS' is case insensitive
        query = db.select("name AS my_name", "age As user_age").from_(users)
        sql = query.sql

        self.assertIn('"name" AS "my_name"', sql)
        self.assertIn('"age" AS "user_age"', sql)

    def test_select_with_column_object(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Test selecting with Column object
        query = db.select(users.name, users.age).from_(users)
        sql = query.sql

        self.assertIn('"name"', sql)
        self.assertIn('"age"', sql)

    def test_select_with_alias_method(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Test selecting with .as_() method
        query = db.select(users.name.as_("my_name")).from_(users)
        sql = query.sql

        self.assertIn('"name" AS "my_name"', sql)

    def test_select_mixed_columns_and_strings(self):
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Test mixing Column objects, Alias objects, and strings
        query = db.select(users.id, users.name.as_("user_name"), "age").from_(users)
        sql = query.sql

        self.assertIn('"id"', sql)
        self.assertIn('"name" AS "user_name"', sql)
        self.assertIn('"age"', sql)

    def test_select_column_with_join(self):
        users = TableFromModel(User)
        pets = TableFromModel(Pet)
        db = DjazzleQuery()

        # Test Column objects in joins
        query = db.select(users.name, pets.name.as_("pet_name")).from_(users).left_join(pets, eq(users.id, pets.owner_id))
        sql = query.sql

        self.assertIn('"name"', sql)
        self.assertIn('"name" AS "pet_name"', sql)
        self.assertIn("LEFT JOIN", sql)


class AsyncDjazzleTestCase(TestCase):
    """Test async query execution support."""

    @classmethod
    def setUpTestData(cls):
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

    async def test_async_select_query(self):
        """Test async SELECT queries using await syntax."""
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Use await syntax without () - this calls __await__() which uses _aexecute()
        rows = await db.select("id", "name", "age").from_(users).where(eq(users.name, "AsyncUser1"))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "AsyncUser1")
        self.assertEqual(rows[0]["age"], 25)

    async def test_async_select_all(self):
        """Test async SELECT * query."""
        users = TableFromModel(User)
        db = DjazzleQuery()

        rows = await db.select().from_(users)

        # Should have at least our 2 test users
        async_users = [r for r in rows if r["name"].startswith("AsyncUser")]
        self.assertGreaterEqual(len(async_users), 2)

    async def test_async_select_as_model(self):
        """Test async SELECT returning model instances."""
        users = TableFromModel(User)
        db = DjazzleQuery()

        rows = await db.select().from_(users).where(eq(users.name, "AsyncUser2")).as_model()

        self.assertEqual(len(rows), 1)
        user = rows[0]
        self.assertIsInstance(user, User)
        self.assertEqual(user.name, "AsyncUser2")
        self.assertEqual(user.age, 30)

    async def test_async_insert(self):
        """Test async INSERT query."""
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Insert without returning
        result = await db.insert(users).values({
            "name": "AsyncInsert",
            "age": 35,
            "email": "asyncinsert@example.com",
            "username": "async_insert",
            "address": "789 Insert Ln"
        })

        self.assertIsNone(result)

        # Verify it was inserted
        rows = await db.select().from_(users).where(eq(users.name, "AsyncInsert"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "AsyncInsert")
        self.assertEqual(rows[0]["age"], 35)

    async def test_async_insert_with_returning(self):
        """Test async INSERT with RETURNING clause."""
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Insert with returning (PostgreSQL)
        result = await db.insert(users).values({
            "name": "AsyncReturn",
            "age": 40,
            "email": "asyncreturn@example.com",
            "username": "async_return",
            "address": "321 Return Rd"
        }).returning()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "AsyncReturn")
        self.assertEqual(result[0]["age"], 40)
        self.assertIsNotNone(result[0]["id"])

    async def test_async_update(self):
        """Test async UPDATE query."""
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Create a user to update
        user = await User.objects.acreate(
            name="AsyncUpdateTest",
            age=20,
            email="asyncupdate@example.com",
            username="async_update",
            address="111 Update St"
        )

        # Update using Djazzle
        result = await db.update(users).set({"age": 21}).where(eq(users.id, user.id))
        self.assertIsNone(result)

        # Verify the update
        rows = await db.select().from_(users).where(eq(users.id, user.id))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["age"], 21)

        # Clean up
        await user.adelete()

    async def test_async_update_with_returning(self):
        """Test async UPDATE with RETURNING clause."""
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Create a user to update
        user = await User.objects.acreate(
            name="AsyncUpdateReturn",
            age=50,
            email="asyncupdatereturn@example.com",
            username="async_update_return",
            address="222 Update Ave"
        )

        # Update with returning (PostgreSQL)
        result = await db.update(users).set({"age": 51}).where(
            eq(users.id, user.id)
        ).returning()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["age"], 51)
        self.assertEqual(result[0]["id"], user.id)

        # Clean up
        await user.adelete()

    async def test_async_delete(self):
        """Test async DELETE query."""
        users = TableFromModel(User)
        db = DjazzleQuery()

        # Create a user to delete
        user = await User.objects.acreate(
            name="AsyncDeleteTest",
            age=60,
            email="asyncdelete@example.com",
            username="async_delete",
            address="333 Delete Blvd"
        )

        # Delete using Djazzle
        result = await db.delete(users).where(eq(users.id, user.id))
        self.assertIsNone(result)

        # Verify it was deleted
        rows = await db.select().from_(users).where(eq(users.id, user.id))
        self.assertEqual(len(rows), 0)

    async def test_async_bulk_insert(self):
        """Test async bulk INSERT."""
        users = TableFromModel(User)
        db = DjazzleQuery()

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

        result = await db.insert(users).values(values)
        self.assertIsNone(result)

        # Verify they were inserted
        rows = await db.select().from_(users)
        bulk_users = [r for r in rows if r["name"].startswith("AsyncBulk")]
        self.assertEqual(len(bulk_users), 5)

        # Clean up
        await User.objects.filter(name__startswith="AsyncBulk").adelete()
