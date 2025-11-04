from .columns import Column
from typing import Any


class Condition:
    """Represents a SQL WHERE condition."""

    def __init__(self, column: Column, operator: str, value):
        self.column = column
        self.operator = operator
        self.value = value

    def to_sql(self):
        # Check if value is a Column (for JOINs)
        if isinstance(self.value, Column):
            # For JOINs, output the column reference directly
            return (
                f"{self.column.full_name()} {self.operator} {self.value.full_name()}",
                None,
            )
        else:
            # For regular conditions, use parameterized query
            return f"{self.column.full_name()} {self.operator} %s", self.value


class NullCondition(Condition):
    """Represents IS NULL or IS NOT NULL conditions."""

    def __init__(self, column: Column, operator: str):
        self.column = column
        self.operator = operator
        self.value = None

    def to_sql(self):
        return f"{self.column.full_name()} {self.operator}", None


class InCondition(Condition):
    """Represents IN or NOT IN conditions."""

    def __init__(self, column: Column, values: list[Any], not_in: bool = False):
        self.column = column
        self.operator = "NOT IN" if not_in else "IN"
        self.value = values

    def to_sql(self):
        placeholders = ", ".join(["%s"] * len(self.value))
        return f"{self.column.full_name()} {self.operator} ({placeholders})", self.value


class BetweenCondition(Condition):
    """Represents a BETWEEN condition."""

    def __init__(self, column: Column, start: Any, end: Any):
        self.column = column
        self.operator = "BETWEEN"
        self.value = (start, end)

    def to_sql(self):
        return f"{self.column.full_name()} BETWEEN %s AND %s", self.value


class CompoundCondition:
    """Represents a compound condition (AND/OR)."""

    def __init__(self, operator: str, *conditions: Condition):
        self.operator = operator
        self.conditions = conditions
        self.column = None  # Compound conditions don't have a single column

    def to_sql(self):
        """
        Returns the SQL clause and a flat list of all parameters.
        """
        clauses = []
        params = []

        for cond in self.conditions:
            clause, value = cond.to_sql()
            clauses.append(f"({clause})")

            # Handle different value types
            if value is None:
                pass
            elif isinstance(value, (list, tuple)):
                params.extend(value)
            else:
                params.append(value)

        combined_clause = f" {self.operator} ".join(clauses)
        return combined_clause, params


def eq(column: Column, value):
    return Condition(column, "=", value)


def lt(column: Column, value):
    return Condition(column, "<", value)


def gte(column: Column, value):
    return Condition(column, ">=", value)


def ne(column: Column, value):
    return Condition(column, "<>", value)


def gt(column: Column, value):
    """Greater than."""
    return Condition(column, ">", value)


def lte(column: Column, value):
    """Less than or equal."""
    return Condition(column, "<=", value)


def like(column: Column, pattern: str):
    """Pattern matching with LIKE."""
    return Condition(column, "LIKE", pattern)


def ilike(column: Column, pattern: str):
    """Case-insensitive pattern matching with ILIKE (PostgreSQL)."""
    return Condition(column, "ILIKE", pattern)


def is_null(column: Column):
    """Check if column IS NULL."""
    return NullCondition(column, "IS NULL")


def is_not_null(column: Column):
    """Check if column IS NOT NULL."""
    return NullCondition(column, "IS NOT NULL")


def in_array(column: Column, values: list[Any]):
    """Check if column value is IN a list of values."""
    return InCondition(column, values, not_in=False)


def not_in_array(column: Column, values: list[Any]):
    """Check if column value is NOT IN a list of values."""
    return InCondition(column, values, not_in=True)


def between(column: Column, start: Any, end: Any):
    """Check if column value is BETWEEN start and end (inclusive)."""
    return BetweenCondition(column, start, end)


def and_(*conditions: Condition | CompoundCondition):
    """
    Combine multiple conditions with AND logic.

    Example:
        and_(eq(users.id, 42), eq(users.name, 'Dan'))
        # Generates: WHERE (id = 42) AND (name = 'Dan')
    """
    return CompoundCondition("AND", *conditions)


def or_(*conditions: Condition | CompoundCondition):
    """
    Combine multiple conditions with OR logic.

    Example:
        or_(eq(users.id, 42), eq(users.name, 'Dan'))
        # Generates: WHERE (id = 42) OR (name = 'Dan')
    """
    return CompoundCondition("OR", *conditions)
