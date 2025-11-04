from uuid import UUID
from django.db import models


class Column:
    """Represents a table column for Djazzle queries."""

    def __init__(self, table_name: str, column_name: str, django_field=None):
        self.table_name = table_name
        self.column_name = column_name
        self.django_field = django_field

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

    @property
    def valid_types(self) -> tuple:
        """
        Return a tuple of valid Python types for this column based on its Django field type.
        Always includes None if the field is nullable.
        """
        if not self.django_field:
            # If no Django field is available, allow any type
            return (object,)

        # Map Django field types to Python types
        field_type_map = {
            models.CharField: (str,),
            models.TextField: (str,),
            models.EmailField: (str,),
            models.URLField: (str,),
            models.SlugField: (str,),
            models.IntegerField: (int,),
            models.BigIntegerField: (int,),
            models.SmallIntegerField: (int,),
            models.PositiveIntegerField: (int,),
            models.PositiveBigIntegerField: (int,),
            models.PositiveSmallIntegerField: (int,),
            models.FloatField: (float, int),
            models.DecimalField: (float, int),
            models.BooleanField: (bool,),
            models.DateField: (str,),  # Can accept strings or date objects
            models.DateTimeField: (str,),  # Can accept strings or datetime objects
            models.TimeField: (str,),  # Can accept strings or time objects
            models.DurationField: (str,),
            models.BinaryField: (bytes,),
            models.UUIDField: (str, UUID),
            models.JSONField: (dict, list, str, int, float, bool),
            models.ForeignKey: (int, str, UUID),
            models.OneToOneField: (int, str, UUID),
        }

        # Get the base field type
        field_class = type(self.django_field)

        # Find the matching type mapping
        valid = None
        for field_type, python_types in field_type_map.items():
            if isinstance(self.django_field, field_type):
                valid = python_types
                break

        # Default to allowing any type if we don't have a specific mapping
        if valid is None:
            valid = (object,)

        # If field is nullable, add None to the valid types
        if hasattr(self.django_field, 'null') and self.django_field.null:
            valid = valid + (type(None),)

        return valid


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
