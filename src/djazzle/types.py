from typing import TypedDict, Any, TypeVar, TYPE_CHECKING
from django.db import models
import sys

RowType = TypeVar("RowType")


def typed_dict_from_model(
    model_cls: type[models.Model], fields: list[str] | None = None
) -> type[TypedDict]:
    """Generate a TypedDict dynamically for static type checkers."""
    field_names = fields or [
        f.name for f in model_cls._meta.get_fields() if hasattr(f, "column")
    ]

    # Create the TypedDict with proper field types
    field_types = {}
    for field_name in field_names:
        try:
            field = model_cls._meta.get_field(field_name)
            if hasattr(field, "null") and field.null:
                field_types[field_name] = Any | None
            else:
                field_types[field_name] = Any
        except Exception:
            field_types[field_name] = Any

    # For runtime, create a simple TypedDict
    row_type = TypedDict(f"{model_cls.__name__}Row", field_types)

    # Store in module for potential IDE discovery
    if TYPE_CHECKING:
        module = sys.modules[model_cls.__module__]
        setattr(module, f"{model_cls.__name__}Row", row_type)

    return row_type
