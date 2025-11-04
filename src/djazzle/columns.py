class Column:
    """Represents a table column for Djazzle queries."""

    def __init__(self, table_name: str, column_name: str):
        self.table_name = table_name
        self.column_name = column_name

    def full_name(self) -> str:
        return f'"{self.column_name}"'

    def as_(self, alias_name: str) -> "Alias":
        """
        Create an aliased version of this column.

        Example:
            db.select(users.name.as_("my_name")).from_(users)()
            # SELECT "name" AS "my_name" FROM "users"
        """
        return Alias(self, alias_name)


class OrderDirection:
    """Represents a column with an order direction (ASC or DESC)."""

    def __init__(self, column: Column, direction: str = "ASC"):
        self.column = column
        self.direction = direction.upper()

    def to_sql(self) -> str:
        return f"{self.column.full_name()} {self.direction}"


class Alias:
    """Represents a column with an alias."""

    def __init__(self, column: Column, alias_name: str):
        self.column = column
        self.alias_name = alias_name

    def to_sql(self) -> str:
        return f'{self.column.full_name()} AS "{self.alias_name}"'


def asc(column: Column) -> OrderDirection:
    """Create an ascending order direction for a column."""
    return OrderDirection(column, "ASC")


def desc(column: Column) -> OrderDirection:
    """Create a descending order direction for a column."""
    return OrderDirection(column, "DESC")


def alias(column: Column, alias_name: str) -> Alias:
    """
    Create an aliased column for use in SELECT.

    Example:
        db.select(alias(users.name, "my_name")).from_(users)()
        # SELECT "name" AS "my_name" FROM "users"
    """
    return Alias(column, alias_name)
