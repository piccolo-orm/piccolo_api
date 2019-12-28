import datetime
import json
import typing as t

from piccolo.columns.operators import (
    LessThan,
    LessEqualThan,
    GreaterThan,
    GreaterEqualThan,
    Equal,
)
from piccolo.columns import Where
from piccolo.table import Table
from piccolo.columns.column_types import Varchar, Text
import pydantic
from pydantic.error_wrappers import ValidationError
from starlette.exceptions import HTTPException
from starlette.routing import Router, Route
from starlette.responses import JSONResponse, Response
from starlette.requests import Request

from .serializers import create_pydantic_model, Config

if t.TYPE_CHECKING:
    from starlette.routing import BaseRoute


DictAny = t.Dict[str, t.Any]


class CustomJSONResponse(Response):
    media_type = "application/json"


OPERATOR_MAP = {
    "lt": LessThan,
    "lte": LessEqualThan,
    "gt": GreaterThan,
    "gte": GreaterEqualThan,
    "e": Equal,
}


class PiccoloCRUD(Router):
    """
    Wraps a Piccolo table with CRUD methods for use in a REST API.
    """

    def __init__(self, table: Table, read_only: bool = True) -> None:
        """
        :params read_only: If True, only the GET method is allowed.
        """
        self.table = table

        routes: t.List[BaseRoute] = [
            Route(
                path="/",
                endpoint=self.root,
                methods=["GET"] if read_only else ["GET", "POST", "DELETE"],
            ),
            Route(
                path="/{row_id:int}/",
                endpoint=self.detail,
                methods=["GET"] if read_only else ["GET", "PUT", "DELETE"],
            ),
            Route(path="/schema/", endpoint=self.get_schema, methods=["GET"]),
            Route(path="/ids/", endpoint=self.get_ids, methods=["GET"]),
        ]
        if not read_only:
            routes += [
                Route(
                    path="/new/",
                    endpoint=self.new,
                    methods=["GET"]
                    if read_only
                    else ["GET", "POST", "DELETE"],
                ),
            ]

        super().__init__(routes=routes)

    ###########################################################################

    @property
    def pydantic_model(self) -> t.Type[pydantic.BaseModel]:
        return create_pydantic_model(self.table)

    @property
    def pydantic_model_optional(self):
        """
        A pydantic model, but all fields are optional. Useful for serialising
        filters, where a user can filter on any number of fields.
        """
        return create_pydantic_model(self.table, all_optional=True)

    def pydantic_model_plural(self, include_readable=False):
        """
        This is for when we want to serialise many copies of the model.
        """
        base_model = create_pydantic_model(
            self.table,
            include_default_columns=True,
            include_readable=include_readable,
        )
        return pydantic.create_model(
            str(self.table.__name__) + "Plural",
            __config__=Config,
            rows=(t.List[base_model], None),
        )

    async def get_schema(self, request: Request):
        """
        Return a representation of the model, so a UI can generate a form.
        """
        return JSONResponse(self.pydantic_model.schema())

    ###########################################################################

    async def get_ids(self, request: Request):
        """
        Returns all the IDs for the current table, mapped to a readable
        representation e.g. {'1': 'joebloggs'}. Used for UI, like foreign
        key selectors.
        """
        query = self.table.select().columns(
            self.table.id, self.table.get_readable()
        )
        values = await query.run()
        return JSONResponse({i["id"]: i["readable"] for i in values})

    ###########################################################################

    async def root(self, request: Request):
        if request.method == "GET":
            print(request.query_params)
            params = dict(request.query_params)
            return await self._get_all(params=params)
        elif request.method == "POST":
            data = await request.json()
            return await self._post_single(data)
        elif request.method == "DELETE":
            return await self._delete_all()

    ###########################################################################

    @staticmethod
    def _split_params(params: DictAny) -> DictAny:
        """
        Some parameters reference fields, and others provide instructions
        on how to perform the query (e.g. which operator to use). An example
        of an operator parameter is {'age__operator': 'gte'}.

        This method splits the params into their different types, and returns
        a dict of dicts.
        """
        response: DictAny = {
            "operators": {},
            "fields": {},
            "include_readable": False,
        }

        for key, value in params.items():
            if key.endswith("__operator") and value in OPERATOR_MAP.keys():
                field_name = key.split("__operator")[0]
                response["operators"][field_name] = value
                continue

            if key == "readable" and value in ("true", "True", "1"):
                response["include_readable"] = True
                continue

            response["fields"][key] = value

        return response

    async def _get_all(self, params: t.Optional[t.Dict[str, t.Any]] = None):
        """
        Get all rows - query parameters are used for filtering.
        """
        params = self._clean_data(params) if params else {}

        split_params = self._split_params(params)

        include_readable = split_params["include_readable"]
        if include_readable:
            readable_columns = [
                self.table._get_related_readable(i)
                for i in self.table._meta.foreign_key_columns
            ]
            columns = self.table._meta.columns + readable_columns
            query = self.table.select(*columns)
        else:
            query = self.table.select()

        query = query.order_by(self.table.id, ascending=False)

        # Apply filters
        fields = split_params["fields"]
        operators = split_params["operators"]
        if fields:
            model_dict = self.pydantic_model_optional(**fields).dict()
            for field_name in fields.keys():
                value = model_dict[field_name]
                if isinstance(
                    self.table._meta.get_column_by_name(field_name),
                    (Varchar, Text),
                ):
                    query = query.where(
                        getattr(self.table, field_name).ilike(f"%{value}%")
                    )
                else:
                    operator_name = operators.get(field_name, "e")
                    operator = OPERATOR_MAP[operator_name]
                    column = getattr(self.table, field_name)
                    query = query.where(
                        Where(column=column, value=value, operator=operator)
                    )

        rows = await query.run()
        # We need to serialise it ourselves, in case there are datetime
        # fields.
        json = self.pydantic_model_plural(include_readable=include_readable)(
            rows=rows
        ).json()
        return CustomJSONResponse(json)

    ###########################################################################

    def _clean_data(self, data: t.Dict[str, t.Any]):
        cleaned_data: t.Dict[str, t.Any] = {}

        for key, value in data.items():
            value = None if value == "null" else value
            cleaned_data[key] = value

        return cleaned_data

    async def _post_single(self, data: t.Dict[str, t.Any]):
        """
        Adds a single row, if the id doesn't already exist.
        """
        cleaned_data = self._clean_data(data)
        try:
            model = self.pydantic_model(**cleaned_data)
        except ValidationError as exception:
            # TODO - use exception.json()
            raise HTTPException(400, str(exception))

        try:
            row = self.table(**model.dict())
            response = await row.save().run()
            # Returns the id of the inserted row.
            return JSONResponse(response)
        except ValueError:
            raise HTTPException(500, "Unable to save the row.")

        return JSONResponse(row)

    async def _delete_all(self):
        """
        Deletes all rows - query parameters are used for filtering.
        """
        # Get ids of deleted rows???
        response = await self.table.delete().run()
        return JSONResponse(response)

    ###########################################################################

    async def new(self, request: Request):
        """
        This endpoint is used when creating new rows in a UI. It provides
        all of the default values for a new row, but doesn't save it.
        """

        def default(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()

        row = self.table(ignore_missing=True)
        row_dict = row.__dict__
        del row_dict["id"]

        return CustomJSONResponse(json.dumps(row_dict, default=default))

    ###########################################################################

    async def detail(self, request: Request):
        row_id = request.path_params.get("row_id", None)
        if row_id is None:
            raise HTTPException(404, "Missing row ID parameter.")

        if (type(row_id) is int) and row_id < 1:
            raise HTTPException(400, "Row ID must be greater than 0")

        if request.method == "GET":
            return await self._get_single(row_id)
        elif request.method == "PUT":
            data = await request.json()
            return await self._put_single(row_id, data)
        elif request.method == "DELETE":
            return await self._delete_single(row_id)

    async def _get_single(self, row_id: int):
        """
        Returns a single row.
        """
        try:
            row = (
                await self.table.select()
                .where(self.table.id == row_id)
                .first()
                .run()
            )
        except ValueError:
            raise HTTPException(404, "Unable to find a row with that ID.")

        return CustomJSONResponse(self.pydantic_model(**row).json())

    async def _put_single(self, row_id: int, data: t.Dict[str, t.Any]):
        """
        Inserts or updates single row.
        """
        cleaned_data = self._clean_data(data)

        try:
            model = self.pydantic_model(**cleaned_data)
        except ValidationError as exception:
            raise HTTPException(400, str(exception))

        try:
            row = self.table(**model.dict())
            row.id = row_id
            response = await row.save().run()
            # Returns the id of the inserted row.
            return JSONResponse(response)
        except ValueError:
            raise HTTPException(500, "Unable to save the row.")

        return JSONResponse(row)

    async def _delete_single(self, row_id: int):
        """
        Deletes a single row.
        """
        try:
            response = (
                await self.table.delete().where(self.table.id == row_id).run()
            )
            # Returns the id of the deleted row.
            return JSONResponse(response)
        except ValueError:
            raise HTTPException(500, "Unable to delete the row.")


__all__ = ["PiccoloCRUD"]
