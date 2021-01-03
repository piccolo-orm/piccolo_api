from __future__ import annotations
from functools import lru_cache
import typing as t
import uuid

from asyncpg.pgproto.pgproto import UUID
from piccolo.columns.column_types import ForeignKey, Text
from piccolo.table import Table
import pydantic


class Config(pydantic.BaseConfig):
    json_encoders = {uuid.UUID: lambda i: str(i), UUID: lambda i: str(i)}
    arbitrary_types_allowed = True


@lru_cache()
def create_pydantic_model(
    table: t.Type[Table],
    include_default_columns: bool = False,
    include_readable: bool = False,
    all_optional: bool = False,
    model_name: t.Optional[str] = None,
) -> t.Type[pydantic.BaseModel]:
    """
    Create a Pydantic model representing a table.

    :param table:
        The Piccolo ``Table`` you want to create a Pydantic serialiser model
        for.
    :param include_default_columns:
        Whether to include columns like ``id`` in the serialiser. You will
        typically include these columns in GET requests, but don't require
        them in POST requests.
    :param include_readable:
        Whether to include 'readable' columns, which give a string
        representation of a foreign key.
    :param all_optional:
        If True, all fields are optional. Useful for filters etc.
    :param model_name:
        By default, the classname of the Piccolo ``Table`` will be used, but
        you can override it if you want multiple Pydantic models based off the
        same Piccolo table.
    :returns:
        A Pydantic model.

    """
    columns: t.Dict[str, t.Any] = {}
    piccolo_columns = (
        table._meta.columns
        if include_default_columns
        else table._meta.non_default_columns
    )

    for column in piccolo_columns:
        column_name = column._meta.name
        is_optional = True if all_optional else not column._meta.required

        _type = (
            t.Optional[column.value_type] if is_optional else column.value_type
        )

        params: t.Dict[str, t.Any] = {
            "default": None if is_optional else ...,
            "nullable": column._meta.null,
        }

        if isinstance(column, ForeignKey):
            tablename = (
                column._foreign_key_meta.resolved_references._meta.tablename
            )
            field = pydantic.Field(
                extra={"foreign_key": True, "to": tablename},
                **params,
            )
            if include_readable:
                columns[f"{column_name}_readable"] = (str, None)
        elif isinstance(column, Text):
            field = pydantic.Field(format="text-area", extra={}, **params)
        else:
            field = pydantic.Field(extra={}, **params)

        columns[column_name] = (_type, field)

    model_name = model_name if model_name else table.__name__

    return pydantic.create_model(model_name, __config__=Config, **columns)
