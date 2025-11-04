from typing import TypeVar, Generic, Type, TYPE_CHECKING, overload
from django.db import models
from .columns import Column

T = TypeVar("T", bound=models.Model)

if TYPE_CHECKING:
    from .types import typed_dict_from_model


class TableFromModel(Generic[T]):
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class
        self.db_table_name = model_class._meta.db_table
        self.column_names = set()

        for field in model_class._meta.get_fields():
            if hasattr(field, "column") and field.column:
                col = Column(self.db_table_name, field.column, django_field=field)
                setattr(self, field.name, col)
                self.column_names.add(field.name)

                # For ForeignKey fields, also create a _id field
                if isinstance(field, models.ForeignKey):
                    # Django creates an {field_name}_id column for foreign keys
                    id_field_name = f"{field.name}_id"
                    id_col = Column(self.db_table_name, f"{field.column}_id", django_field=field)
                    setattr(self, id_field_name, id_col)
                    self.column_names.add(id_field_name)

        # TYPE_CHECKING-only RowType for editor hints
        if TYPE_CHECKING:
            self.RowType = typed_dict_from_model(model_class, list(self.column_names))


# Factory function for proper typing
if TYPE_CHECKING:

    @overload
    def table_from_model(model_class: Type[T]) -> TableFromModel[T]: ...


def table_from_model(model_class):
    """Create a properly typed table from a Django model."""
    return TableFromModel(model_class)
