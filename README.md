# Djazzle

Djazzle is a Drizzle-inspired query builder for Django projects.

## Features

- Django model introspection
- Type-safe returns
- Hybrid model/dict return
- Chainable, Drizzle-inspired API
- **Significantly faster than Django ORM** (37-81% faster in benchmarks)
- Works with PostgreSQL, MySQL, and SQLite

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
db = DjazzleQuery()

# SELECT queries
rows = db.select("id", "name").from_(users).where(eq(users.id, 42))()
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
```

See [benchmarks/README.md](benchmarks/README.md) for detailed performance analysis.

### Running Benchmarks

```bash
python run_benchmarks.py \
  --records 10000
  --iterations 200
  --format markdown
```

This will generate detailed performance reports in JSON, CSV, and Markdown formats.
