from django.db import connection
from typing import TypeVar, Dict, Any, Union, Optional
from .table import TableFromModel
from .conditions import Condition, CompoundCondition
from .exceptions import InvalidColumnError
from django.db import models
from .columns import Column, OrderDirection, Alias
from asgiref.sync import sync_to_async
from .connection import ConnectionAdapter


T = TypeVar("T", bound=models.Model)


class DjazzleQuery:
    """Main query builder for Djazzle."""

    def __init__(self, conn=None):
        """
        Initialize a DjazzleQuery instance.

        Args:
            conn: Database connection. Can be:
                - None (uses Django's default connection)
                - Django connection object
                - psycopg2 connection (PostgreSQL - sync only)
                - psycopg3 connection (PostgreSQL - sync or async)
                - mysqlclient connection (MySQLdb - sync only)
                - pymysql connection (MySQL - sync only)
                - aiomysql connection (MySQL - async only)
                - asyncmy connection (MySQL - async only)
        """
        # Use Django default connection if none provided
        raw_conn = conn or connection
        self.conn_adapter = ConnectionAdapter(raw_conn)
        self.conn = raw_conn  # Keep reference to raw connection for compatibility
        self._table: TableFromModel | None = None
        self._fields: list[str | Column | Alias] | None = None
        self._conditions: list[Condition | CompoundCondition] = []
        self._as_model: bool = False
        self._limit: int | None = None
        self._offset: int | None = None
        self._order_by: list[Column | OrderDirection] = []
        self._distinct: bool = False
        # Insert-specific state
        self._query_type: str = "select"  # "select", "insert", "update", or "delete"
        self._insert_values: list[Dict[str, Any]] | None = None
        self._returning_fields: list[str] | None = None
        # Update-specific state
        self._update_values: Dict[str, Any] | None = None
        # Join state
        self._joins: list[tuple[str, TableFromModel, Condition]] = (
            []
        )  # (join_type, table, condition)

    def _reset_query_state(self):
        """Reset query state when starting a new query."""
        self._fields = None
        self._conditions = []
        self._limit = None
        self._offset = None
        self._order_by = []
        self._distinct = False
        self._insert_values = None
        self._update_values = None
        self._returning_fields = None
        self._joins = []

    def select(self, *fields: Union[str, Column, Alias]) -> "DjazzleQuery":
        self._reset_query_state()
        self._query_type = "select"
        self._fields = list(fields) if fields else None
        return self

    def select_distinct(self, *fields: Union[str, Column, Alias]) -> "DjazzleQuery":
        """Select distinct values from the specified fields."""
        self._reset_query_state()
        self._query_type = "select"
        self._fields = list(fields) if fields else None
        self._distinct = True
        return self

    def insert(self, table: TableFromModel) -> "DjazzleQuery":
        """
        Start an INSERT query for the given table.

        Example:
            db.insert(users).values({"name": "Andrew", "age": 25})
        """
        self._reset_query_state()
        self._query_type = "insert"
        self._table = table
        return self

    def values(self, data: Dict[str, Any] | list[Dict[str, Any]]) -> "DjazzleQuery":
        """
        Specify values to insert. Can be a single dict or a list of dicts for bulk insert.

        Examples:
            # Single row
            db.insert(users).values({"name": "Andrew"})

            # Multiple rows
            db.insert(users).values([{"name": "Andrew"}, {"name": "Dan"}])
        """
        if isinstance(data, dict):
            self._insert_values = [data]
        elif isinstance(data, list):
            self._insert_values = data
        else:
            raise ValueError("values() must receive a dict or list of dicts")

        # Validate types for each row
        self._validate_value_types(self._insert_values)

        return self

    def returning(self, *fields: str) -> "DjazzleQuery":
        """
        Specify which fields to return after INSERT/UPDATE (PostgreSQL).
        If no fields specified, returns all fields.

        Example:
            db.insert(users).values({"name": "Dan"}).returning()
            db.insert(users).values({"name": "Dan"}).returning("id", "name")
        """
        self._returning_fields = list(fields) if fields else ["*"]
        return self

    def update(self, table: TableFromModel) -> "DjazzleQuery":
        """
        Start an UPDATE query for the given table.

        Example:
            db.update(users).set({"name": "Mr. Dan"}).where(eq(users.name, "Dan"))
        """
        self._reset_query_state()
        self._query_type = "update"
        self._table = table
        return self

    def set(self, data: Dict[str, Any]) -> "DjazzleQuery":
        """
        Specify values to update. Keys should match column names.
        Values of None will set the column to NULL.

        Example:
            db.update(users).set({"name": "Mr. Dan", "age": 30})
        """
        if not isinstance(data, dict):
            raise ValueError("set() must receive a dict")
        # Filter out None values are actually kept (to set NULL)
        # But we could filter undefined if we had a special sentinel
        self._update_values = data

        # Validate types
        self._validate_value_types([data])

        return self

    def delete(self, table: TableFromModel) -> "DjazzleQuery":
        """
        Start a DELETE query for the given table.

        Example:
            # Delete all rows
            db.delete(users)()

            # Delete with conditions
            db.delete(users).where(eq(users.name, "Dan"))()
        """
        self._reset_query_state()
        self._query_type = "delete"
        self._table = table
        return self

    def from_(self, table: TableFromModel) -> "DjazzleQuery":
        self._table = table
        return self

    def where(self, *conditions: Condition | CompoundCondition) -> "DjazzleQuery":
        self._conditions.extend(conditions)
        return self

    def left_join(self, table: TableFromModel, condition: Condition) -> "DjazzleQuery":
        """
        Add a LEFT JOIN to the query.

        Example:
            db.select().from_(users).left_join(pets, eq(users.id, pets.owner_id))
        """
        self._joins.append(("LEFT", table, condition))
        return self

    def right_join(self, table: TableFromModel, condition: Condition) -> "DjazzleQuery":
        """
        Add a RIGHT JOIN to the query.

        Example:
            db.select().from_(users).right_join(pets, eq(users.id, pets.owner_id))
        """
        self._joins.append(("RIGHT", table, condition))
        return self

    def inner_join(self, table: TableFromModel, condition: Condition) -> "DjazzleQuery":
        """
        Add an INNER JOIN to the query.

        Example:
            db.select().from_(users).inner_join(pets, eq(users.id, pets.owner_id))
        """
        self._joins.append(("INNER", table, condition))
        return self

    def full_join(self, table: TableFromModel, condition: Condition) -> "DjazzleQuery":
        """
        Add a FULL JOIN to the query.

        Example:
            db.select().from_(users).full_join(pets, eq(users.id, pets.owner_id))
        """
        self._joins.append(("FULL", table, condition))
        return self

    def as_model(self, value: bool = True) -> "DjazzleQuery":
        self._as_model = value
        return self

    def limit(self, count: int) -> "DjazzleQuery":
        """Set the LIMIT clause for the query."""
        self._limit = count
        return self

    def offset(self, count: int) -> "DjazzleQuery":
        """Set the OFFSET clause for the query."""
        self._offset = count
        return self

    def order_by(self, *columns: Column | OrderDirection) -> "DjazzleQuery":
        """
        Set the ORDER BY clause for the query.

        Can accept Column objects (which default to ASC) or OrderDirection objects
        created with asc() or desc() helper functions.

        Examples:
            query.order_by(users.name)  # ORDER BY name ASC
            query.order_by(desc(users.name))  # ORDER BY name DESC
            query.order_by(users.name, desc(users.age))  # Multiple columns
        """
        self._order_by.extend(columns)
        return self

    def _validate_value_types(self, rows: list[Dict[str, Any]]) -> None:
        """
        Validate that the types of values match the expected types for each column.

        Args:
            rows: List of dictionaries with column names as keys and values to validate

        Raises:
            TypeError: If a value's type doesn't match the column's valid types
        """
        if not self._table:
            return  # Can't validate without table

        for row_idx, row in enumerate(rows):
            for col_name, value in row.items():
                # Get the column object from the table
                if not hasattr(self._table, col_name):
                    # Column validation will catch this later
                    continue

                column = getattr(self._table, col_name)
                if not isinstance(column, Column):
                    continue

                # Check if the value type is valid
                valid_types = column.valid_types
                if not isinstance(value, valid_types):
                    # Build a helpful error message
                    type_names = ", ".join(t.__name__ for t in valid_types)
                    actual_type = type(value).__name__
                    row_info = f" (row {row_idx})" if len(rows) > 1 else ""
                    raise TypeError(
                        f"Invalid type for column '{col_name}'{row_info}: "
                        f"expected {type_names}, got {actual_type}"
                    )

    def _validate_columns(self):
        if not self._table:
            raise ValueError("No table selected")
        valid_columns = self._table.column_names

        # Validate selected fields
        if self._fields:
            for f in self._fields:
                # Skip validation for Column and Alias objects (they're already validated)
                if isinstance(f, (Column, Alias)):
                    continue
                # Skip validation for qualified column names (table.column)
                if "." in f:
                    continue
                # Skip validation for aliased columns (column as alias)
                if " as " in f.lower():
                    # Extract the column part before 'as'
                    parts = f.split()
                    as_index = next(i for i, p in enumerate(parts) if p.lower() == "as")
                    col_name = " ".join(parts[:as_index])
                    # Skip if it's a qualified name
                    if "." in col_name:
                        continue
                    # Validate the actual column name
                    if col_name not in self._table.column_names:
                        raise InvalidColumnError(
                            f"Column {col_name} not in model {self._table.db_table_name}"
                        )
                    continue
                if f not in self._table.column_names:
                    raise InvalidColumnError(
                        f"Column {f} not in model {self._table.db_table_name}"
                    )

        # Validate condition columns (including nested compound conditions)
        def validate_condition(cond):
            if isinstance(cond, CompoundCondition):
                # Recursively validate nested conditions
                for nested_cond in cond.conditions:
                    validate_condition(nested_cond)
            else:
                col_name = getattr(cond.column, "column_name", None)
                if col_name and col_name not in valid_columns:
                    raise InvalidColumnError(f"Invalid column in condition: {col_name}")

        for cond in self._conditions:
            validate_condition(cond)

        # Validate order by columns
        for order_item in self._order_by:
            if isinstance(order_item, OrderDirection):
                col_name = order_item.column.column_name
            else:
                col_name = order_item.column_name
            if col_name not in valid_columns:
                raise InvalidColumnError(f"Invalid column in order by: {col_name}")

    def _build_sql(self) -> tuple[str, list[Any]]:
        """
        Build the SQL query and return the SQL string and parameters.

        Returns:
            tuple[str, list[Any]]: A tuple of (sql_string, parameters)
        """
        if not self._table:
            raise ValueError("No table selected")

        if self._query_type == "insert":
            return self._build_insert_sql()
        elif self._query_type == "update":
            return self._build_update_sql()
        elif self._query_type == "delete":
            return self._build_delete_sql()
        else:
            return self._build_select_sql()

    def _build_select_sql(self) -> tuple[str, list[Any]]:
        """Build a SELECT query."""
        self._validate_columns()

        # Handle field selection - support strings, Column objects, Alias objects
        if self._fields:
            field_parts = []
            for f in self._fields:
                # Handle Alias objects
                if isinstance(f, Alias):
                    field_parts.append(f.to_sql())
                # Handle Column objects
                elif isinstance(f, Column):
                    field_parts.append(f.full_name())
                # Handle string field names
                elif isinstance(f, str):
                    # Check if it contains an alias (column as alias)
                    if " as " in f.lower():
                        # Split on 'as' (case insensitive)
                        parts = f.split()
                        as_index = next(
                            i for i, p in enumerate(parts) if p.lower() == "as"
                        )
                        col_part = " ".join(parts[:as_index])
                        alias_part = parts[as_index + 1]

                        # Handle qualified column name in the column part
                        if "." in col_part:
                            table_name, col_name = col_part.rsplit(".", 1)
                            field_parts.append(
                                f'"{table_name}"."{col_name}" AS "{alias_part}"'
                            )
                        else:
                            field_parts.append(f'"{col_part}" AS "{alias_part}"')
                    # Check if it's a qualified column name (table.column)
                    elif "." in f:
                        table_name, col_name = f.rsplit(".", 1)
                        field_parts.append(f'"{table_name}"."{col_name}"')
                    else:
                        field_parts.append(f'"{f}"')
            fields = ", ".join(field_parts)
        else:
            fields = "*"

        distinct_keyword = "DISTINCT " if self._distinct else ""
        sql = f'SELECT {distinct_keyword}{fields} FROM "{self._table.db_table_name}"'
        params: list[Any] = []

        # Add JOIN clauses
        for join_type, join_table, join_condition in self._joins:
            join_clause, join_value = join_condition.to_sql()
            sql += f' {join_type} JOIN "{join_table.db_table_name}" ON {join_clause}'
            # Handle join condition parameters
            if join_value is not None:
                if isinstance(join_value, (list, tuple)):
                    params.extend(join_value)
                else:
                    params.append(join_value)

        if self._conditions:
            clauses = []
            for cond in self._conditions:
                clause, value = cond.to_sql()
                clauses.append(clause)
                # Handle different value types (None, list/tuple, or single value)
                if value is None:
                    # IS NULL / IS NOT NULL conditions have no parameters
                    pass
                elif isinstance(value, (list, tuple)):
                    # IN, NOT IN, BETWEEN conditions have multiple parameters
                    params.extend(value)
                else:
                    # Regular conditions have a single parameter
                    params.append(value)
            sql += " WHERE " + " AND ".join(clauses)

        # Add ORDER BY clause
        if self._order_by:
            order_clauses = []
            for order_item in self._order_by:
                if isinstance(order_item, OrderDirection):
                    order_clauses.append(order_item.to_sql())
                else:
                    # If it's a plain Column, default to ASC
                    order_clauses.append(f"{order_item.full_name()} ASC")
            sql += " ORDER BY " + ", ".join(order_clauses)

        # Add LIMIT clause
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"

        # Add OFFSET clause
        if self._offset is not None:
            sql += f" OFFSET {self._offset}"

        return sql, params

    def _build_insert_sql(self) -> tuple[str, list[Any]]:
        """Build an INSERT query."""
        if not self._insert_values:
            raise ValueError("No values specified for INSERT")

        # Get all unique columns from all rows, preserving order from first row
        # then adding any additional columns from subsequent rows
        columns = []
        seen = set()
        for row in self._insert_values:
            for col in row.keys():
                if col not in seen:
                    columns.append(col)
                    seen.add(col)

        # Validate columns exist in table
        valid_columns = self._table.column_names
        for col in columns:
            if col not in valid_columns:
                raise InvalidColumnError(
                    f"Column {col} not in model {self._table.db_table_name}"
                )

        # Build INSERT statement
        column_list = ", ".join(f'"{col}"' for col in columns)
        sql = f'INSERT INTO "{self._table.db_table_name}" ({column_list})'

        # Build VALUES clause
        params: list[Any] = []
        value_rows = []
        for row in self._insert_values:
            row_placeholders = []
            for col in columns:
                value = row.get(col, None)  # Use None for missing columns
                row_placeholders.append("%s")
                params.append(value)
            value_rows.append(f"({', '.join(row_placeholders)})")

        sql += " VALUES " + ", ".join(value_rows)

        # Add RETURNING clause (PostgreSQL)
        if self._returning_fields is not None:
            if "*" in self._returning_fields:
                sql += " RETURNING *"
            else:
                returning_cols = ", ".join(f'"{f}"' for f in self._returning_fields)
                sql += f" RETURNING {returning_cols}"

        return sql, params

    def _build_update_sql(self) -> tuple[str, list[Any]]:
        """Build an UPDATE query."""
        if not self._update_values:
            raise ValueError("No values specified for UPDATE. Use .set()")

        # Validate columns exist in table
        valid_columns = self._table.column_names
        for col in self._update_values.keys():
            if col not in valid_columns:
                raise InvalidColumnError(
                    f"Column {col} not in model {self._table.db_table_name}"
                )

        # Build UPDATE statement
        sql = f'UPDATE "{self._table.db_table_name}"'
        params: list[Any] = []

        # Build SET clause
        set_clauses = []
        for col, value in self._update_values.items():
            set_clauses.append(f'"{col}" = %s')
            params.append(value)

        sql += " SET " + ", ".join(set_clauses)

        # Add WHERE clause
        if self._conditions:
            clauses = []
            for cond in self._conditions:
                clause, value = cond.to_sql()
                clauses.append(clause)
                # Handle different value types (None, list/tuple, or single value)
                if value is None:
                    pass
                elif isinstance(value, (list, tuple)):
                    params.extend(value)
                else:
                    params.append(value)
            sql += " WHERE " + " AND ".join(clauses)

        # Add LIMIT clause
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"

        # Add RETURNING clause (PostgreSQL)
        if self._returning_fields is not None:
            if "*" in self._returning_fields:
                sql += " RETURNING *"
            else:
                returning_cols = ", ".join(f'"{f}"' for f in self._returning_fields)
                sql += f" RETURNING {returning_cols}"

        return sql, params

    def _build_delete_sql(self) -> tuple[str, list[Any]]:
        """Build a DELETE query."""
        # Build DELETE statement
        sql = f'DELETE FROM "{self._table.db_table_name}"'
        params: list[Any] = []

        # Add WHERE clause
        if self._conditions:
            clauses = []
            for cond in self._conditions:
                clause, value = cond.to_sql()
                clauses.append(clause)
                # Handle different value types (None, list/tuple, or single value)
                if value is None:
                    pass
                elif isinstance(value, (list, tuple)):
                    params.extend(value)
                else:
                    params.append(value)
            sql += " WHERE " + " AND ".join(clauses)

        # Add LIMIT clause
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"

        # Add RETURNING clause (PostgreSQL)
        if self._returning_fields is not None:
            if "*" in self._returning_fields:
                sql += " RETURNING *"
            else:
                returning_cols = ", ".join(f'"{f}"' for f in self._returning_fields)
                sql += f" RETURNING {returning_cols}"

        return sql, params

    @property
    def sql(self) -> str:
        """
        Get the SQL query string without executing it.

        Returns:
            str: The SQL query string

        Example:
            query = db.select("id", "name").from_(users).where(eq(users.id, 42))
            print(query.sql)  # SELECT "id", "name" FROM "users" WHERE "id" = %s
        """
        sql, _ = self._build_sql()
        return sql

    @property
    def params(self) -> list[Any]:
        """
        Get the query parameters without executing the query.

        Returns:
            list[Any]: The list of parameters for the query

        Example:
            query = db.select().from_(users).where(eq(users.id, 42))
            print(query.params)  # [42]
        """
        _, params = self._build_sql()
        return params

    def _execute(self):
        sql, params = self._build_sql()

        # Check for async connection
        if self.conn_adapter.is_async:
            raise RuntimeError(
                f"Cannot use synchronous execute() with async connection type '{self.conn_adapter.conn_type}'. "
                f"Use await syntax instead: await query()"
            )

        # Use connection adapter to get cursor
        with self.conn_adapter.cursor() as cur:
            cur.execute(sql, params)

            if self._query_type == "insert":
                # Handle INSERT queries
                if self._returning_fields is not None:
                    # RETURNING clause specified, fetch results
                    columns = [desc[0] for desc in cur.description]
                    results = [dict(zip(columns, row)) for row in cur.fetchall()]
                    return results
                else:
                    # No RETURNING, return None
                    return None
            elif self._query_type == "update":
                # Handle UPDATE queries
                if self._returning_fields is not None:
                    # RETURNING clause specified, fetch results
                    columns = [desc[0] for desc in cur.description]
                    results = [dict(zip(columns, row)) for row in cur.fetchall()]
                    return results
                else:
                    # No RETURNING, return None
                    return None
            elif self._query_type == "delete":
                # Handle DELETE queries
                if self._returning_fields is not None:
                    # RETURNING clause specified, fetch results
                    columns = [desc[0] for desc in cur.description]
                    results = [dict(zip(columns, row)) for row in cur.fetchall()]
                    return results
                else:
                    # No RETURNING, return None
                    return None
            else:
                # Handle SELECT queries
                columns = [desc[0] for desc in cur.description]

                if self._as_model:
                    # Use from_db() for faster model instantiation - bypasses __init__
                    model_cls: type[models.Model] = self._table.model_class
                    db_alias = self.conn_adapter.get_db_alias()
                    return [
                        model_cls.from_db(db_alias, columns, row)
                        for row in cur.fetchall()
                    ]
                else:
                    results = [dict(zip(columns, row)) for row in cur.fetchall()]
                    return results

    async def _aexecute(self):
        """
        Async version of query execution.

        Supports:
        - Django async connections (using sync_to_async)
        - Native async connections (aiomysql, asyncmy)

        Returns:
            Query results (same format as synchronous execution)

        Note:
            For Django connections, this method uses sync_to_async to safely
            execute database operations in async contexts. It obtains the
            database connection inside the sync context to avoid thread-safety
            issues, as per Django 5.2+ guidelines.
        """
        sql, params = self._build_sql()

        # Handle native async connections (aiomysql, asyncmy)
        if self.conn_adapter.is_async:
            return await self._execute_native_async(sql, params)

        # Handle Django connections with sync_to_async
        query_type = self._query_type
        returning_fields = self._returning_fields
        as_model = self._as_model
        table = self._table
        conn_adapter = self.conn_adapter

        # Use sync_to_async to wrap the synchronous database operation
        # IMPORTANT: We must get the connection inside the sync context, not pass it
        # across thread boundaries. Django's connection is thread-local.
        @sync_to_async
        def execute_query():
            # Get the thread-local connection inside the sync context
            # This is critical for thread safety in Django 5.2+
            from django.db import connection as thread_local_conn

            with thread_local_conn.cursor() as cur:
                cur.execute(sql, params)

                if query_type == "insert":
                    # Handle INSERT queries
                    if returning_fields is not None:
                        # RETURNING clause specified, fetch results
                        columns = [desc[0] for desc in cur.description]
                        results = [dict(zip(columns, row)) for row in cur.fetchall()]
                        return results
                    else:
                        # No RETURNING, return None
                        return None
                elif query_type == "update":
                    # Handle UPDATE queries
                    if returning_fields is not None:
                        # RETURNING clause specified, fetch results
                        columns = [desc[0] for desc in cur.description]
                        results = [dict(zip(columns, row)) for row in cur.fetchall()]
                        return results
                    else:
                        # No RETURNING, return None
                        return None
                elif query_type == "delete":
                    # Handle DELETE queries
                    if returning_fields is not None:
                        # RETURNING clause specified, fetch results
                        columns = [desc[0] for desc in cur.description]
                        results = [dict(zip(columns, row)) for row in cur.fetchall()]
                        return results
                    else:
                        # No RETURNING, return None
                        return None
                else:
                    # Handle SELECT queries
                    columns = [desc[0] for desc in cur.description]

                    if as_model:
                        # Use from_db() for faster model instantiation - bypasses __init__
                        model_cls: type[models.Model] = table.model_class
                        db_alias = conn_adapter.get_db_alias()
                        return [
                            model_cls.from_db(db_alias, columns, row)
                            for row in cur.fetchall()
                        ]
                    else:
                        results = [dict(zip(columns, row)) for row in cur.fetchall()]
                        return results

        return await execute_query()

    async def _execute_native_async(self, sql: str, params: list[Any]):
        """
        Execute query using native async connections (aiomysql, asyncmy).

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            Query results
        """
        # Get async cursor using context manager
        async with await self.conn_adapter.async_cursor() as cur:
            await cur.execute(sql, params)

            if self._query_type == "insert":
                # Handle INSERT queries
                if self._returning_fields is not None:
                    # RETURNING clause specified, fetch results
                    columns = [desc[0] for desc in cur.description]
                    results = [dict(zip(columns, row)) for row in await cur.fetchall()]
                    return results
                else:
                    # No RETURNING, return None
                    return None
            elif self._query_type == "update":
                # Handle UPDATE queries
                if self._returning_fields is not None:
                    # RETURNING clause specified, fetch results
                    columns = [desc[0] for desc in cur.description]
                    results = [dict(zip(columns, row)) for row in await cur.fetchall()]
                    return results
                else:
                    # No RETURNING, return None
                    return None
            elif self._query_type == "delete":
                # Handle DELETE queries
                if self._returning_fields is not None:
                    # RETURNING clause specified, fetch results
                    columns = [desc[0] for desc in cur.description]
                    results = [dict(zip(columns, row)) for row in await cur.fetchall()]
                    return results
                else:
                    # No RETURNING, return None
                    return None
            else:
                # Handle SELECT queries
                columns = [desc[0] for desc in cur.description]

                if self._as_model:
                    # Use from_db() for faster model instantiation - bypasses __init__
                    model_cls: type[models.Model] = self._table.model_class
                    db_alias = self.conn_adapter.get_db_alias()
                    return [
                        model_cls.from_db(db_alias, columns, row)
                        for row in await cur.fetchall()
                    ]
                else:
                    results = [dict(zip(columns, row)) for row in await cur.fetchall()]
                    return results

    def __await__(self):
        """
        Allow using the query with await syntax.

        Example:
            result = await db.select().from_(users)()
        """
        return self._aexecute().__await__()

    def __call__(self):
        return self._execute()
