from __future__ import annotations
from functools import lru_cache
import json
import typing as t
import uuid

from asyncpg.pgproto.pgproto import UUID
from piccolo.columns.column_types import (
    Array,
    ForeignKey,
    Text,
    Decimal,
    Numeric,
    Varchar,
    Secret,
    JSON,
    JSONB,
)
from piccolo.utils.encoding import load_json
from piccolo.table import Table
import pydantic


class Config(pydantic.BaseConfig):
    json_encoders = {uuid.UUID: lambda i: str(i), UUID: lambda i: str(i)}
    arbitrary_types_allowed = True


def pydantic_json_validator(cls, value):
    try:
        load_json(value)
    except json.JSONDecodeError:
        raise ValueError("Unable to parse the JSON.")
    else:
        return value


@lru_cache()
def create_pydantic_model(
    table: t.Type[Table],
    include_default_columns: bool = False,
    include_readable: bool = False,
    all_optional: bool = False,
    model_name: t.Optional[str] = None,
    deserialize_json: bool = False,
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
    :param deserialize_json:
        By default, the values of any Piccolo JSON or JSONB columns are
        returned as strings. By setting this parameter to True, they will be
        returned as objects.
    :returns:
        A Pydantic model.

    """
    columns: t.Dict[str, t.Any] = {}
    validators: t.Dict[str, classmethod] = {}
    piccolo_columns = (
        table._meta.columns
        if include_default_columns
        else table._meta.non_default_columns
    )

    for column in piccolo_columns:
        column_name = column._meta.name
        is_optional = True if all_optional else not column._meta.required

        #######################################################################

        # Work out the column type

        if isinstance(column, (Decimal, Numeric)):
            value_type: t.Type = pydantic.condecimal(
                max_digits=column.precision, decimal_places=column.scale
            )
        elif isinstance(column, Varchar):
            value_type = pydantic.constr(max_length=column.length)
        elif isinstance(column, Array):
            value_type = t.List[column.base_column.value_type]  # type: ignore
        elif isinstance(column, (JSON, JSONB)):
            if deserialize_json:
                value_type = pydantic.Json
            else:
                value_type = column.value_type
                validators[f"{column_name}_is_json"] = pydantic.validator(
                    column_name, allow_reuse=True
                )(pydantic_json_validator)
        else:
            value_type = column.value_type

        _type = t.Optional[value_type] if is_optional else value_type

        #######################################################################

        params: t.Dict[str, t.Any] = {
            "default": None if is_optional else ...,
            "nullable": column._meta.null,
        }

        extra = {
            "help_text": column._meta.help_text,
            "choices": column._meta.get_choices_dict(),
        }

        if isinstance(column, ForeignKey):
            tablename = (
                column._foreign_key_meta.resolved_references._meta.tablename
            )
            field = pydantic.Field(
                extra={"foreign_key": True, "to": tablename, **extra},
                **params,
            )
            if include_readable:
                columns[f"{column_name}_readable"] = (str, None)
        elif isinstance(column, Text):
            field = pydantic.Field(format="text-area", extra=extra, **params)
        elif isinstance(column, Secret):
            field = pydantic.Field(extra={"secret": True, **extra})
        else:
            field = pydantic.Field(extra=extra, **params)

        columns[column_name] = (_type, field)

    model_name = model_name if model_name else table.__name__

    class CustomConfig(Config):
        schema_extra = {"help_text": table._meta.help_text}

    return pydantic.create_model(
        model_name,
        __config__=CustomConfig,
        __validators__=validators,
        **columns,
    )
