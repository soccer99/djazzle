# Custom Database Connections

Djazzle supports using your own database connections instead of Django's default connection. This is useful when you want to:

- Use a different database than your Django settings
- Manage connection pools yourself
- Use native async database drivers
- Integrate with existing database connection code

## Supported Connection Types

- **Django connections** (default) - Standard Django database connections
- **psycopg2** - PostgreSQL driver (sync only)
- **psycopg3** - Modern PostgreSQL driver (sync and async)
- **mysqlclient** - MySQL driver (MySQLdb - sync only)
- **pymysql** - Pure Python MySQL driver (sync only)
- **aiomysql** - Async MySQL driver (async only)
- **asyncmy** - Another async MySQL driver (async only)

## Usage Examples

### Django Connection (Default)

```python
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

# Uses Django's default connection
db = DjazzleQuery()
results = db.select().from_(users)()
```

### Custom Django Connection

```python
from django.db import connections
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

# Use a specific Django connection from settings
db = DjazzleQuery(conn=connections['other_db'])
results = db.select().from_(users)()
```

### psycopg2 (PostgreSQL - Sync Only)

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

### pymysql

```python
import pymysql
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

# Create your own pymysql connection
conn = pymysql.connect(
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

### aiomysql (Async)

```python
import asyncio
import aiomysql
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

async def main():
    # Create async connection
    conn = await aiomysql.connect(
        host="localhost",
        user="myuser",
        password="mypass",
        db="mydb"
    )

    # Pass it to Djazzle
    db = DjazzleQuery(conn=conn)

    # Use await syntax for queries
    results = await db.select().from_(users)
    print(results)

    conn.close()

asyncio.run(main())
```

### asyncmy (Async)

```python
import asyncio
import asyncmy
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

async def main():
    # Create async connection
    conn = await asyncmy.connect(
        host="localhost",
        user="myuser",
        password="mypass",
        database="mydb"
    )

    # Pass it to Djazzle
    db = DjazzleQuery(conn=conn)

    # Use await syntax for queries
    results = await db.select().from_(users)
    print(results)

    await conn.close()

asyncio.run(main())
```

## Connection Pooling

When using custom connections, you're responsible for managing connection pooling:

### psycopg with Connection Pool

```python
from psycopg_pool import ConnectionPool
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

# Create a connection pool
pool = ConnectionPool("dbname=mydb user=myuser password=mypass")

# Get a connection from the pool
with pool.connection() as conn:
    db = DjazzleQuery(conn=conn)
    results = db.select().from_(users)()

pool.close()
```

### aiomysql with Connection Pool

```python
import asyncio
import aiomysql
from djazzle import DjazzleQuery, TableFromModel
from myapp.models import User

users = TableFromModel(User)

async def main():
    # Create async connection pool
    pool = await aiomysql.create_pool(
        host="localhost",
        user="myuser",
        password="mypass",
        db="mydb",
        minsize=1,
        maxsize=10
    )

    # Get connection from pool
    async with pool.acquire() as conn:
        db = DjazzleQuery(conn=conn)
        results = await db.select().from_(users)
        print(results)

    pool.close()
    await pool.wait_closed()

asyncio.run(main())
```

## Important Notes

1. **Django Models**: Djazzle still uses Django models for schema information via `TableFromModel`, but you can execute queries against any compatible database connection.

2. **Async vs Sync**:
   - Sync connections (psycopg, mysqlclient, pymysql) must use the sync call syntax: `query()`
   - Async connections (aiomysql, asyncmy) must use await syntax: `await query`
   - Mixing sync and async will raise an error

3. **Model Instantiation**: When using `.as_model()`, the database alias will be:
   - For Django connections: uses the actual connection alias
   - For custom connections: defaults to `'default'`

4. **Connection Management**: You're responsible for:
   - Opening and closing connections
   - Managing connection pools
   - Handling connection errors
   - Transaction management

5. **Database Compatibility**: Djazzle generates SQL that should work across PostgreSQL, MySQL, and SQLite, but some features (like `RETURNING` clause) are PostgreSQL-specific.
