"""
Simple typing utilities for Djazzle.
"""

from typing import TypeVar, TYPE_CHECKING, Type, overload
from django.db import models

T = TypeVar("T", bound=models.Model)

if TYPE_CHECKING:
    from .table import TableFromModel


@overload
def create_typed_table(model_class: Type[T]) -> "TableFromModel[T]": ...


def create_typed_table(model_class):
    """Create a typed table from a Django model."""
    from .table import TableFromModel

    return TableFromModel(model_class)


def create_typed_query():
    """Create a DjazzleQuery instance."""
    from .query import DjazzleQuery

    return DjazzleQuery()


# Export for users
__all__ = [
    "create_typed_table",
    "create_typed_query",
]
