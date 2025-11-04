# Djazzle

Djazzle is a Drizzle-inspired query builder for Django projects.

## Features

- Django model introspection
- Type-safe returns
- Hybrid model/dict return
- Chainable, Drizzle-inspired API
- **Full async/await support** for modern Django applications
- **Runtime type checking** for INSERT and UPDATE operations
- **Significantly faster than Django ORM** (up to 76% faster in benchmarks)
- Works with PostgreSQL, MySQL, and SQLite

## Why?

The Django ORM is great, but if you've used SQL directly or other query builders like SQLAlchemy or Drizzle, 
you might find yourself wanting something different.

Djazzle gives you a query builder that looks and feels more like raw SQL. 
If you're the type who thinks in SQL rather than Django's abstraction, this will feel more natural. 
You write queries that map pretty directly to the SQL that gets executed, which makes it easier to reason about what's actually happening.

You don't have to switch completely, this can work in tandem with the Django ORM if you want.

It also encourages you to be explicit about what data you're loading. 
With the ORM, it's easy to accidentally fetch entire model instances when you only need a couple fields. 
Djazzle makes it obvious when you're selecting everything vs. just the columns you need.

Performance-wise, it's faster than the Django ORM (see the benchmarks below). 
For most apps this won't matter much, but we want to keep pushing the boundaries of what Django can do.
We need to continue making improvements if we want to stay relevant when the topic of conversation is always with speed-focused frameworks
like Node's Fastify and Hono, or the Rust/Go web frameworks.

Finally, if you're coming from another ecosystem—especially if you're used to SQLAlchemy or similar query builders—Djazzle will feel more familiar than Django's ORM syntax. It's nice to have an option that might make Django more approachable to folks from other backgrounds.

## Q&A

> Why not just use raw SQL?
>
> You can! But Djazzle gives you type safety, automatic parameter binding, and integrates with your Django models. It's a middle ground between raw SQL and the full ORM.

> Does this work with my existing Django project?
>
> Yes. Djazzle works alongside the Django ORM—you don't have to replace anything. Just import it and use it where you want. Your models, migrations, and everything else stay exactly the same.

> Can I still use Django's relationships and foreign keys?
>
> Djazzle uses your Django models, so all your relationships are there. For querying across relationships, you'll use JOINs instead of Django's `select_related` or `prefetch_related`. Check out the JOIN examples in the API reference.

> Is this production ready?
>
> It works, but it's a new project. Test it thoroughly before using it in production. The API might change as we get feedback from real usage.

> Did you use AI?
>
> Yes. I came up with the idea and then used a mix of ChatGPT and Claude Code to set this up. I steered it in the direction I wanted, and made a lot of changes myself until I was happy with it.


## Database Compatibility

Djazzle works with all Django-supported databases, but some features have database-specific limitations:

| Feature | PostgreSQL | MySQL | SQLite |
|---------|-----------|-------|--------|
| SELECT queries | ✅ | ✅ | ✅ |
| INSERT queries | ✅ | ✅ | ✅ |
| UPDATE queries | ✅ | ✅ | ✅ |
| DELETE queries | ✅ | ✅ | ✅ |
| WHERE conditions | ✅ | ✅ | ✅ |
| LIMIT / OFFSET | ✅ | ✅ | ✅ |
| ORDER BY | ✅ | ✅ | ✅ |
| **RETURNING clause** | ✅ | ❌ | ⚠️ (3.35+) |
| **LEFT JOIN** | ✅ | ✅ | ✅ |
| **RIGHT JOIN** | ✅ | ✅ | ⚠️ (3.39+) |
| **INNER JOIN** | ✅ | ✅ | ✅ |
| **FULL JOIN** | ✅ | ❌ | ❌ |
| **LIKE pattern** | ✅ | ✅ | ✅ |
| **ILIKE pattern** | ✅ | ❌ | ❌ |
| **DISTINCT** | ✅ | ✅ | ✅ |

**Note:**
- **RETURNING**: PostgreSQL fully supports RETURNING for INSERT/UPDATE/DELETE. SQLite 3.35+ supports it. MySQL does not support RETURNING.

## Quick Example

```python
from src.djazzle import TableFromModel, DjazzleQuery, eq
from myapp.models import User

users = TableFromModel(User)

# Setup DjazzleQuery with a db connection
# Default is django.db.connections["default"]
# Can also pass in secondary db:
# db = DjazzleQuery(conn=connections['other_db'])
db = DjazzleQuery()

# SELECT queries
rows = db.select(users.id, users.name).from_(users).where(eq(users.id, 42))()
>>> [{ "id": 1, "name": "John" }]

rows = db.select().from_(users).where(eq(users.id, 42)).as_model()()
>>> <User(id=1, name="John")>

# INSERT queries
result = db.insert(users).values({"name": "Andrew", "age": 25}).returning()()
>>> [{"id": 2, "name": "Andrew", "age": 25}]

# UPDATE queries
result = db.update(users).set({"name": "Mr. John"}).where(eq(users.id, 1)).returning()()
>>> [{"id": 1, "name": "Mr. John", "age": 30}]

# DELETE queries
result = db.delete(users).where(eq(users.name, "Andrew")).returning()()
>>> [{"id": 2, "name": "Andrew", "age": 25}]
```

## Runtime Type Checking

Djazzle automatically validates that the values you're inserting or updating match the expected types for each column. This catches type errors before they hit the database, making debugging easier.

### How It Works

When you call `values()` or `set()`, Djazzle checks each value against the Django field type:

```python
users = TableFromModel(User)
db = DjazzleQuery()

# This works fine - age is an integer
db.insert(users).values({"name": "John", "age": 25})()

# This raises TypeError - age should be int, not str
db.insert(users).values({"name": "John", "age": "twenty-five"})()
# TypeError: Invalid type for column 'age': expected int, NoneType, got str
```

### Supported Field Types

Djazzle maps Django field types to Python types automatically:

- **CharField, TextField, EmailField**: expects `str`
- **IntegerField, BigIntegerField**: expects `int`
- **FloatField, DecimalField**: expects `float` or `int`
- **BooleanField**: expects `bool`
- **DateField, DateTimeField, TimeField**: expects `str` (or date/datetime objects)
- **JSONField**: expects `dict`, `list`, `str`, `int`, `float`, or `bool`
- **ForeignKey**: expects `int` (the foreign key ID)

### Nullable Fields

If a field has `null=True`, the type checker automatically allows `None`:

```python
# Assuming age has null=True
db.insert(users).values({"name": "John", "age": None})()  # Works fine
```

### Bulk Inserts

Type checking works with bulk inserts too, and the error message tells you which row failed:

```python
db.insert(users).values([
    {"name": "User 1", "age": 25},
    {"name": "User 2", "age": "thirty"},  # Wrong type
])()
# TypeError: Invalid type for column 'age' (row 1): expected int, NoneType, got str
```

### Updates

Type checking applies to `set()` as well:

```python
db.update(users).set({"age": "thirty"}).where(eq(users.id, 1))()
# TypeError: Invalid type for column 'age': expected int, NoneType, got str
```

## Async Support

Djazzle fully supports async/await syntax, making it perfect for async Django views and APIs. The async implementation uses Django's `sync_to_async` to safely execute database operations in async contexts.

### Basic Async Usage

To use Djazzle asynchronously, simply use `await` with your query (without calling `()`):

```python
from src.djazzle import TableFromModel, DjazzleQuery, eq
from myapp.models import User

users = TableFromModel(User)
db = DjazzleQuery()

# Async SELECT
async def get_user(user_id):
    rows = await db.select().from_(users).where(eq(users.id, user_id))
    return rows[0] if rows else None

# Async INSERT
async def create_user(name, age):
    result = await db.insert(users).values({
        "name": name,
        "age": age,
        "email": f"{name}@example.com",
        "username": name.lower(),
        "address": "123 Main St"
    }).returning()
    return result[0]

# Async UPDATE
async def update_user_age(user_id, new_age):
    await db.update(users).set({"age": new_age}).where(eq(users.id, user_id))

# Async DELETE
async def delete_user(user_id):
    await db.delete(users).where(eq(users.id, user_id))
```

### Sync vs Async Syntax

**Synchronous** (use `()` to execute):
```python
rows = db.select().from_(users)()
```

**Asynchronous** (use `await` without `()`):
```python
rows = await db.select().from_(users)
```

### Async with Django Views

Perfect for async Django views:

```python
from django.http import JsonResponse
from src.djazzle import TableFromModel, DjazzleQuery, eq
from .models import User

async def user_detail(request, user_id):
    users = TableFromModel(User)
    db = DjazzleQuery()

    rows = await db.select().from_(users).where(eq(users.id, user_id))

    if not rows:
        return JsonResponse({"error": "User not found"}, status=404)

    return JsonResponse(rows[0])
```

### Async Model Instances

You can also return Django model instances asynchronously:

```python
async def get_user_models():
    users = TableFromModel(User)
    db = DjazzleQuery()

    # Returns list of User model instances
    user_objects = await db.select().from_(users).as_model()
    return user_objects
```

### Important Notes

- **Don't mix syntax**: When using `await`, omit the `()` call operator
- **Works with all query types**: SELECT, INSERT, UPDATE, DELETE all support async
- **Thread-safe**: Uses `sync_to_async` for proper thread isolation
- **Django 4.2+ compatible**: Follows Django's async best practices by obtaining database connections inside the sync context, avoiding thread-safety issues
- **Same performance**: Async queries are as fast as synchronous ones

### Technical Details

Djazzle's async implementation follows Django 4.2+ guidelines for safe async database access:

1. **Thread-local connections**: The async implementation obtains database connections from Django's thread-local storage inside the `sync_to_async` wrapper, not from the query builder's state
2. **No connection sharing**: Database connection objects are never passed across thread boundaries
3. **Proper isolation**: Each async query executes in its own thread-safe context using Django's connection management

This design ensures compatibility with Django's async views, middleware, and the ASGI server ecosystem.

## Custom Database Connections

While Djazzle uses Django's default database connection out of the box, you can also use your own database connections. This is useful when you want to:

- Use a different database than your Django settings
- Manage connection pools yourself
- Use native async database drivers
- Integrate with existing database connection code

### Supported Connection Types

- **Django connections** (default) - Standard Django database connections
- **psycopg2** - PostgreSQL driver (sync only)
- **psycopg3** - Modern PostgreSQL driver (sync and async)
- **mysqlclient** - MySQL driver (sync only)
- **pymysql** - Pure Python MySQL driver (sync only)
- **aiomysql** - Async MySQL driver (async only)
- **asyncmy** - Another async MySQL driver (async only)

### Django database connections (default)

```python
from django.db import connections
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

# The default connection if nothing is passed in is django.db.connections["default"]
# You may use a specific Django connection from your settings.DATABASES
db = DjazzleQuery(conn=connections['other_db'])
results = db.select().from_(users)()
```

### psycopg2 (PostgreSQL - Sync)

```python
import psycopg2
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

# Create your own psycopg2 connection
conn = psycopg2.connect("dbname=mydb user=myuser password=mypass")

# Pass it to Djazzle
db = DjazzleQuery(conn=conn)
results = db.select().from_(users)()

conn.close()
```

### psycopg3 (PostgreSQL - Sync)

```python
import psycopg
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

# Create your own psycopg3 connection
conn = psycopg.connect("dbname=mydb user=myuser password=mypass")

# Pass it to Djazzle
db = DjazzleQuery(conn=conn)
results = db.select().from_(users)()

conn.close()
```

### psycopg3 (PostgreSQL - Async)

```python
import asyncio
import psycopg
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

async def main():
    # Create async connection using psycopg3
    async with await psycopg.AsyncConnection.connect(
        "dbname=mydb user=myuser password=mypass"
    ) as conn:
        # Pass it to Djazzle
        db = DjazzleQuery(conn=conn)

        # Use await syntax for queries
        results = await db.select().from_(users)
        print(results)

asyncio.run(main())
```

### mysqlclient (MySQLdb)

```python
import MySQLdb
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

# Create your own MySQLdb connection
conn = MySQLdb.connect(
    host="localhost",
    user="myuser",
    password="mypass",
    database="mydb"
)

# Pass it to Djazzle
db = DjazzleQuery(conn=conn)
results = db.select().from_(users)()

conn.close()
```

### Connection Pooling

When using custom connections, you're responsible for managing connection pooling:

```python
# psycopg with Connection Pool
from psycopg_pool import ConnectionPool

pool = ConnectionPool("dbname=mydb user=myuser password=mypass")

with pool.connection() as conn:
    db = DjazzleQuery(conn=conn)
    results = db.select().from_(users)()

pool.close()
```

```python
# aiomysql with Connection Pool
import asyncio
import aiomysql

async def main():
    pool = await aiomysql.create_pool(
        host="localhost",
        user="myuser",
        password="mypass",
        db="mydb",
        minsize=1,
        maxsize=10
    )

    async with pool.acquire() as conn:
        db = DjazzleQuery(conn=conn)
        results = await db.select().from_(users)

    pool.close()
    await pool.wait_closed()
```

### Important Notes

1. **Django Models**: Djazzle still uses Django models for schema information via `TableFromModel`, but you can execute queries against any compatible database connection.

2. **Async vs Sync**:
   - Sync connections (psycopg2, mysqlclient, pymysql) must use the sync call syntax: `query()`
   - Async connections (psycopg3 async, aiomysql, asyncmy) must use await syntax: `await query`
   - Mixing sync and async will raise an error

3. **Connection Management**: You're responsible for opening and closing connections, managing connection pools, handling connection errors, and transaction management.

For more detailed examples and additional database drivers, see [CUSTOM_CONNECTIONS.md](CUSTOM_CONNECTIONS.md).

## API Reference

### Query Methods

#### SELECT Queries

##### `select(*fields)`
Select specific columns from the table. Accepts strings, Column objects, or Alias objects.

```python
# String field names
db.select("id", "name", "email").from_(users)()

# Column objects
db.select(users.id, users.name, users.email).from_(users)()

# Column aliases using .as_()
db.select(users.name.as_("my_name")).from_(users)()
# SELECT "name" AS "my_name" FROM "users"

# Mix of all types
db.select(users.id, users.name.as_("user_name"), "age").from_(users)()
# SELECT "id", "name" AS "user_name", "age" FROM "users"

# With JOINs
db.select(users.name, pets.name.as_("pet_name"))\
    .from_(users)\
    .left_join(pets, eq(users.id, pets.owner_id))()
# SELECT "name", "name" AS "pet_name" FROM "users"
# LEFT JOIN "pets" ON "users"."id" = "pets"."owner_id"
```

**Compatibility:** Column objects and aliases work with all databases (PostgreSQL, MySQL, SQLite).

##### `selectDistinct(*fields)`
Select distinct values from the specified columns.

```python
# Get unique cities
db.selectDistinct("city").from_(users)()

# Get unique city/state combinations
db.selectDistinct("city", "state").from_(users)()
```

#### INSERT Queries

##### `insert(table).values(data)`
Insert one or more rows into a table.

```python
# Insert a single row
db.insert(users).values({"name": "Andrew", "age": 25})()

# Insert multiple rows
db.insert(users).values([
    {"name": "Andrew", "age": 25},
    {"name": "Dan", "age": 30}
])()
```

##### `returning(*fields)`
Return inserted data (PostgreSQL only). If no fields specified, returns all fields.

```python
# Return all fields of inserted row
result = db.insert(users).values({"name": "Dan"}).returning()()
# [{"id": 1, "name": "Dan", "age": None, ...}]

# Return specific fields
result = db.insert(users).values({"name": "Dan"}).returning("id", "name")()
# [{"id": 1, "name": "Dan"}]

# Multiple rows with returning
results = db.insert(users).values([
    {"name": "Andrew"},
    {"name": "Dan"}
]).returning()()
# [{"id": 1, "name": "Andrew", ...}, {"id": 2, "name": "Dan", ...}]
```

**Note:** Without `returning()`, insert queries return `None`.

#### UPDATE Queries

##### `update(table).set(data).where(conditions)`
Update rows in a table.

```python
# Update with WHERE clause
db.update(users).set({"name": "Mr. Dan"}).where(eq(users.name, "Dan"))()

# Update multiple fields
db.update(users).set({
    "name": "Mr. Dan",
    "age": 31
}).where(eq(users.id, 1))()

# Set a field to NULL
db.update(users).set({"age": None}).where(eq(users.id, 1))()
```

##### `returning(*fields)` with UPDATE
Return updated data (PostgreSQL only).

```python
# Return all fields of updated rows
result = db.update(users).set({"age": 31}).where(eq(users.name, "Dan")).returning()()
# [{"id": 1, "name": "Dan", "age": 31, ...}]

# Return specific fields
result = db.update(users).set({"age": 31}).where(eq(users.name, "Dan")).returning("id", "age")()
# [{"id": 1, "age": 31}]
```

##### `limit()` with UPDATE
Limit the number of rows to update (PostgreSQL, MySQL, SQLite).

```python
# Update only first 2 matching rows
db.update(users).set({"verified": True}).where(eq(users.status, "pending")).limit(2)()
```

**Note:** Without `returning()`, update queries return `None`.

#### DELETE Queries

##### `delete(table).where(conditions)`
Delete rows from a table.

```python
# Delete all rows (use with caution!)
db.delete(users)()

# Delete with WHERE clause
db.delete(users).where(eq(users.name, "Dan"))()

# Delete with complex conditions
db.delete(users).where(
    and_(
        lt(users.age, 18),
        eq(users.status, "inactive")
    )
)()
```

##### `returning(*fields)` with DELETE
Return deleted data (PostgreSQL only).

```python
# Return all fields of deleted rows
result = db.delete(users).where(eq(users.name, "Dan")).returning()()
# [{"id": 1, "name": "Dan", "age": 30, ...}]

# Return specific fields
result = db.delete(users).where(eq(users.status, "banned")).returning("id", "name")()
# [{"id": 1, "name": "Dan"}, {"id": 5, "name": "Eve"}]
```

##### `limit()` with DELETE
Limit the number of rows to delete (PostgreSQL, MySQL, SQLite).

```python
# Delete only first 2 matching rows
db.delete(users).where(eq(users.name, "Dan")).limit(2)()
```

**Note:** Without `returning()`, delete queries return `None`.

#### JOIN Queries

##### `left_join(table, condition)`
Perform a LEFT JOIN.

```python
# Basic LEFT JOIN
db.select().from_(users).left_join(pets, eq(users.id, pets.owner_id))()

# With WHERE clause
db.select().from_(users).left_join(pets, eq(users.id, pets.owner_id)).where(eq(users.age, 25))()
```

##### `inner_join(table, condition)`
Perform an INNER JOIN.

```python
db.select().from_(users).inner_join(pets, eq(users.id, pets.owner_id))()
```

##### `right_join(table, condition)`
Perform a RIGHT JOIN.

```python
db.select().from_(users).right_join(pets, eq(users.id, pets.owner_id))()
```

##### `full_join(table, condition)`
Perform a FULL JOIN.

```python
db.select().from_(users).full_join(pets, eq(users.id, pets.owner_id))()
```

##### Partial Select with JOINs
Select specific columns from joined tables using qualified column names:

```python
db.select(
    "users.id",
    "users.name",
    "pets.id",
    "pets.name"
).from_(users).left_join(pets, eq(users.id, pets.owner_id))()

# SQL: SELECT "users"."id", "users"."name", "pets"."id", "pets"."name"
#      FROM "users" LEFT JOIN "pets" ON "users"."id" = "pets"."owner_id"
```

##### Multiple JOINs
Chain multiple JOINs together:

```python
db.select().from_(users)\
    .left_join(pets, eq(users.id, pets.owner_id))\
    .inner_join(orders, eq(users.id, orders.user_id))()
```

#### `where(*conditions)`
Filter results using conditions. Multiple conditions are combined with AND by default.

```python
db.select().from_(users).where(eq(users.age, 25))()
```

#### `limit(count)` / `offset(count)`
Limit and offset results for pagination.

```python
db.select().from_(users).limit(10).offset(20)()
```

#### `order_by(*columns)`
Order results by columns.

```python
from djazzle import asc, desc

db.select().from_(users).order_by(desc(users.created_at))()
db.select().from_(users).order_by(users.name, desc(users.age))()
```

#### `sql` / `params` properties
Inspect the SQL query and parameters before executing.

```python
query = db.select("id", "name").from_(users).where(eq(users.id, 42))

print(query.sql)     # SELECT "id", "name" FROM "users" WHERE "id" = %s
print(query.params)  # [42]

rows = query()  # execute the query

# Complex example
query = db.select().from_(users).where(
    and_(
        in_(users.status, ["active", "pending"]),
        gt(users.age, 18)
    )
).order_by(desc(users.created_at)).limit(10)

print(query.sql)
# SELECT * FROM "users" WHERE ("status" IN (%s, %s)) AND ("age" > %s) ORDER BY "created_at" DESC LIMIT 10
print(query.params)  # ['active', 'pending', 18]
```

### Comparison Operators

All standard SQL comparison operators are available:

```python
from djazzle import eq, ne, lt, lte, gt, gte

# Equal
db.select().from_(users).where(eq(users.id, 42))()

# Not equal
db.select().from_(users).where(ne(users.status, "inactive"))()

# Less than
db.select().from_(users).where(lt(users.age, 18))()

# Less than or equal
db.select().from_(users).where(lte(users.age, 21))()

# Greater than
db.select().from_(users).where(gt(users.score, 100))()

# Greater than or equal
db.select().from_(users).where(gte(users.age, 18))()
```

### Pattern Matching

Use LIKE and ILIKE for pattern matching:

```python
from djazzle import like, ilike

# Case-sensitive pattern matching
db.select().from_(users).where(like(users.name, "John%"))()

# Case-insensitive pattern matching (PostgreSQL)
db.select().from_(users).where(ilike(users.email, "%@gmail.com"))()
```

### NULL Checks

Check for NULL or NOT NULL values:

```python
from djazzle import is_null, is_not_null

# Find users without email
db.select().from_(users).where(is_null(users.email))()

# Find users with email
db.select().from_(users).where(is_not_null(users.email))()
```

### List and Range Operations

#### `in_()` / `notIn()`
Check if a value is in a list:

```python
from djazzle import in_, notIn

# Find users with specific IDs
db.select().from_(users).where(in_(users.id, [1, 2, 3, 4, 5]))()

# Exclude specific statuses
db.select().from_(users).where(notIn(users.status, ["banned", "deleted"]))()
```

#### `between()`
Check if a value is within a range:

```python
from djazzle import between

# Find users between ages 18 and 65
db.select().from_(users).where(between(users.age, 18, 65))()

# Find records in date range
db.select().from_(orders).where(
    between(orders.created_at, start_date, end_date)
)()
```

### Combining Conditions

Use `and_()` and `or_()` to combine multiple conditions with custom logic:

```python
from djazzle import and_, or_, eq, gt, is_not_null

# AND: All conditions must be true
db.select().from_(users).where(
    and_(
        eq(users.id, 42),
        eq(users.name, "Dan")
    )
)()
# SQL: WHERE (id = 42) AND (name = 'Dan')

# OR: At least one condition must be true
db.select().from_(users).where(
    or_(
        eq(users.id, 42),
        eq(users.name, "Dan")
    )
)()
# SQL: WHERE (id = 42) OR (name = 'Dan')

# Complex nested conditions
db.select().from_(users).where(
    and_(
        or_(
            eq(users.status, "active"),
            eq(users.status, "pending")
        ),
        gt(users.age, 18),
        is_not_null(users.email)
    )
)()
# SQL: WHERE ((status = 'active') OR (status = 'pending')) AND (age > 18) AND (email IS NOT NULL)
```

**Note:** When you pass multiple conditions to `where()` without `and_()` or `or_()`, they are automatically combined with AND:

```python
# These are equivalent:
db.select().from_(users).where(eq(users.age, 25), eq(users.city, "NYC"))()
db.select().from_(users).where(and_(eq(users.age, 25), eq(users.city, "NYC")))()
```

## Performance

Djazzle consistently outperforms Django ORM in query execution:

Comparison Summary:
--------------------------------------------------------------------------------

```
Select All Records
  Description: Fetch all 10000 records from database
  Django ORM:  23.8250ms (± 4.7105ms)
  Djazzle:     7.9804ms (± 0.0868ms)
  Result:      Djazzle is 66.50% FASTER

Filtered Query (Single Match)
  Description: WHERE clause returning 1 record
  Django ORM:  0.3361ms (± 0.0100ms)
  Djazzle:     0.3307ms (± 0.1914ms)
  Result:      Djazzle is 1.62% FASTER

Select Specific Columns
  Description: Select 2 columns from 10000 records
  Django ORM:  5.9478ms (± 0.8993ms)
  Djazzle:     5.6321ms (± 1.5506ms)
  Result:      Djazzle is 5.31% FASTER

Return 50 Model object instances
  Description: Query returning 50 rows as Django model instances
  Django ORM:  0.1480ms (± 0.0097ms)
  Djazzle:     0.1031ms (± 0.0044ms)
  Result:      Djazzle is 30.38% FASTER

Limit First 100 Records
  Description: Fetch only first 100 records
  Django ORM:  0.2365ms (± 0.0043ms)
  Djazzle:     0.0892ms (± 0.0010ms)
  Result:      Djazzle is 62.29% FASTER

Order By Name desc
  Description: Order by
  Django ORM:  24.9691ms (± 4.7044ms)
  Djazzle:     9.4522ms (± 0.2500ms)
  Result:      Djazzle is 62.14% FASTER

INSERT Single Record
  Description: Insert one record into database
  Django ORM:  0.0467ms (± 0.0018ms)
  Djazzle:     0.0203ms (± 0.0004ms)
  Result:      Djazzle is 56.54% FASTER

Bulk INSERT (100 records)
  Description: Insert 100 records in one operation
  Django ORM:  2.5146ms (± 1.9854ms)
  Djazzle:     1.8699ms (± 0.0320ms)
  Result:      Djazzle is 25.64% FASTER

UPDATE Single Record
  Description: Update one record in database
  Django ORM:  0.0532ms (± 0.0026ms)
  Djazzle:     0.0124ms (± 0.0010ms)
  Result:      Djazzle is 76.77% FASTER

Bulk UPDATE (100 records)
  Description: Update 100 records in one operation
  Django ORM:  0.2251ms (± 0.0077ms)
  Djazzle:     0.1338ms (± 0.0059ms)
  Result:      Djazzle is 40.55% FASTER
```

See [benchmarks/README.md](benchmarks/README.md) for detailed performance analysis.

### Running Benchmarks

```bash
python run_benchmarks.py \
  --records 10000
  --iterations 200
  --format markdown
```

By default, the benchmarks use sqlite, but you can pass `--use-postgres` to benchmark against a TestContainers Postgres docker database.

This will generate detailed performance reports in JSON, CSV, and Markdown formats.

## Testing

Djazzle includes a comprehensive test suite with support for testing against multiple database backends.

### Run tests with SQLite (default)

```bash
uv run pytest
```

### Run tests with PostgreSQL or MySQL

Test against real PostgreSQL or MySQL databases using testcontainers (requires Docker):

```bash
# Install testcontainers extra
uv sync --extra testcontainers

# Run tests against PostgreSQL
uv run pytest --db postgres

# Run tests against MySQL
uv run pytest --db mysql
```

Testcontainers automatically spins up a Docker container with PostgreSQL or MySQL, runs your tests against it, and tears it down when finished. This ensures you're testing against real database behavior without manual setup.

**Benefits:**
- Tests real database-specific features (like PostgreSQL's `RETURNING` clause)
- Automatic container management
- Clean state for every test session
- No local database setup required

See [TESTING.md](TESTING.md) for detailed testing documentation, including troubleshooting and writing tests for specific databases.
