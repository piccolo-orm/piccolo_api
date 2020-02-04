from __future__ import annotations
from functools import lru_cache
import typing as t
import uuid

from asyncpg.pgproto.pgproto import UUID
from piccolo.columns.column_types import ForeignKey, Text
import pydantic

if t.TYPE_CHECKING:
    from piccolo.table import Table


class Config(pydantic.BaseConfig):
    json_encoders = {uuid.UUID: lambda i: str(i), UUID: lambda i: str(i)}
    arbitrary_types_allowed = True


@lru_cache()
def create_pydantic_model(
    table: Table,
    include_default_columns=False,
    include_readable=False,
    all_optional=False,
) -> t.Type[pydantic.BaseModel]:
    """
    Create a Pydantic model representing a table.

    :param include_default_columns:
        Whether to include columns like 'id' in the serialiser.
    :param include_readable:
        Whether to include 'readable' columns, which give a string
        representation of a foreign key.
    :params all_optional:
        If True, all fields are optional. Useful for filters etc.
    """
    columns: t.Dict[str, t.Any] = {}
    piccolo_columns = (
        table._meta.columns
        if include_default_columns
        else table._meta.non_default_columns
    )

    for column in piccolo_columns:
        column_name = column._meta.name
        is_optional = True if all_optional else column._meta.null

        _type = (
            t.Optional[column.value_type] if is_optional else column.value_type
        )

        params: t.Dict[str, t.Any] = {
            "default": None if is_optional else ...,
            "nullable": column._meta.null,
        }

        if type(column) == ForeignKey:
            field = pydantic.Field(
                extra={
                    "foreign_key": True,
                    "to": column._foreign_key_meta.references._meta.tablename,
                },
                **params,
            )
            if include_readable:
                columns[f"{column_name}_readable"] = (str, None)
        elif type(column) == Text:
            field = pydantic.Field(format="text-area", extra={}, **params)
        else:
            field = pydantic.Field(extra={}, **params)

        columns[column_name] = (_type, field)

    return pydantic.create_model(
        str(table.__name__), __config__=Config, **columns,
    )
