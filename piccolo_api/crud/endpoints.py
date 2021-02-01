from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
import logging
import typing as t

from piccolo.columns.operators import (
    LessThan,
    LessEqualThan,
    GreaterThan,
    GreaterEqualThan,
    Equal,
    Operator,
)
from piccolo.columns import Column, Where
from piccolo.columns.column_types import Varchar, Text
from piccolo.table import Table
import pydantic
from pydantic.error_wrappers import ValidationError
from starlette.routing import Router, Route
from starlette.responses import JSONResponse, Response
from starlette.requests import Request

from .exceptions import MalformedQuery
from .serializers import create_pydantic_model, Config

if t.TYPE_CHECKING:
    from piccolo.query.base import Query
    from starlette.routing import BaseRoute


logger = logging.getLogger(__file__)


OPERATOR_MAP = {
    "lt": LessThan,
    "lte": LessEqualThan,
    "gt": GreaterThan,
    "gte": GreaterEqualThan,
    "e": Equal,
}


MATCH_TYPES = ("contains", "exact", "starts", "ends")


class CustomJSONResponse(Response):
    media_type = "application/json"


@dataclass
class OrderBy:
    ascending: bool = False
    property_name: str = "id"


@dataclass
class Params:
    operators: t.Dict[str, t.Type[Operator]] = field(
        default_factory=lambda: defaultdict(lambda: Equal)
    )
    match_types: t.Dict[str, str] = field(
        default_factory=lambda: defaultdict(lambda: MATCH_TYPES[0])
    )
    fields: t.Dict[str, t.Any] = field(default_factory=dict)
    order_by: t.Optional[OrderBy] = None
    include_readable: bool = False
    page: int = 1
    page_size: t.Optional[int] = None


class PiccoloCRUD(Router):
    """
    Wraps a Piccolo table with CRUD methods for use in a REST API.
    """

    max_page_size: int = 1000

    def __init__(
        self,
        table: t.Type[Table],
        read_only: bool = True,
        allow_bulk_delete: bool = False,
        page_size: int = 15,
    ) -> None:
        """
        :param table:
            The Piccolo ``Table`` to expose CRUD methods for.
        :param read_only:
            If True, only the GET method is allowed.
        :param allow_bulk_delete:
            If True, allows a delete request to the root to delete all matching
            records. It is dangerous, so is disabled by default.
        :param page_size:
            The number of results shown on each page by default.
        """
        self.table = table
        self.page_size = page_size
        self.read_only = read_only
        self.allow_bulk_delete = allow_bulk_delete

        root_methods = ["GET"]
        if not read_only:
            root_methods += (
                ["POST", "DELETE"] if allow_bulk_delete else ["POST"]
            )

        routes: t.List[BaseRoute] = [
            Route(path="/", endpoint=self.root, methods=root_methods),
            Route(
                path="/{row_id:int}/",
                endpoint=self.detail,
                methods=["GET"]
                if read_only
                else ["GET", "PUT", "DELETE", "PATCH"],
            ),
            Route(path="/schema/", endpoint=self.get_schema, methods=["GET"]),
            Route(path="/ids/", endpoint=self.get_ids, methods=["GET"]),
            Route(path="/count/", endpoint=self.get_count, methods=["GET"]),
            Route(
                path="/references/",
                endpoint=self.get_references,
                methods=["GET"],
            ),
            Route(path="/new/", endpoint=self.new, methods=["GET"]),
            Route(
                path="/password/",
                endpoint=self.update_password,
                methods=["PUT"],
            ),
        ]

        super().__init__(routes=routes)

    ###########################################################################

    @property
    def pydantic_model(self) -> t.Type[pydantic.BaseModel]:
        """
        Useful for serialising inbound data from POST and PUT requests.
        """
        return create_pydantic_model(
            self.table, model_name=f"{self.table.__name__}In"
        )

    def _pydantic_model_output(
        self, include_readable: bool = False
    ) -> t.Type[pydantic.BaseModel]:
        return create_pydantic_model(
            self.table,
            include_default_columns=True,
            include_readable=include_readable,
            model_name=f"{self.table.__name__}Output",
        )

    @property
    def pydantic_model_output(self) -> t.Type[pydantic.BaseModel]:
        """
        Contains the default columns, which is required when exporting
        data (for example, in a GET request).
        """
        return self._pydantic_model_output()

    @property
    def pydantic_model_optional(self) -> t.Type[pydantic.BaseModel]:
        """
        All fields are optional, which is useful for serialising filters,
        where a user can filter on any number of fields.
        """
        return create_pydantic_model(
            self.table,
            include_default_columns=True,
            all_optional=True,
            model_name=f"{self.table.__name__}Optional",
        )

    def pydantic_model_plural(self, include_readable=False):
        """
        This is for when we want to serialise many copies of the model.
        """
        base_model = create_pydantic_model(
            self.table,
            include_default_columns=True,
            include_readable=include_readable,
            model_name=f"{self.table.__name__}Item",
        )
        return pydantic.create_model(
            str(self.table.__name__) + "Plural",
            __config__=Config,
            rows=(t.List[base_model], None),
        )

    async def get_schema(self, request: Request) -> JSONResponse:
        """
        Return a representation of the model, so a UI can generate a form.
        """
        return JSONResponse(self.pydantic_model.schema())

    ###########################################################################

    async def update_password(self, request: Request) -> Response:
        """
        Used to update password fields.
        """
        return Response("Coming soon", status_code=501)

    ###########################################################################

    async def get_ids(self, request: Request) -> JSONResponse:
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

    async def get_references(self, request: Request) -> JSONResponse:
        """
        Returns a list of tables with foreign keys to this table, along with
        the name of the foreign key column.
        """
        references = [
            {
                "tableName": i._meta.table._meta.tablename,
                "columnName": i._meta.name,
            }
            for i in self.table._meta.foreign_key_references
        ]
        return JSONResponse({"references": references})

    ###########################################################################

    async def get_count(self, request: Request) -> Response:
        """
        Returns the total number of rows in the table.
        """
        params = dict(request.query_params)
        split_params = self._split_params(params)

        try:
            query = self._apply_filters(self.table.count(), split_params)
        except MalformedQuery as exception:
            return Response(str(exception), status_code=400)

        count = await query.run()
        return JSONResponse({"count": count, "page_size": self.page_size})

    ###########################################################################

    async def root(self, request: Request) -> Response:
        if request.method == "GET":
            params = dict(request.query_params)
            return await self._get_all(params=params)
        elif request.method == "POST":
            data = await request.json()
            return await self._post_single(data)
        elif request.method == "DELETE":
            params = dict(request.query_params)
            return await self._delete_all(params=params)
        else:
            return Response(status_code=405)

    ###########################################################################

    @staticmethod
    def _split_params(params: t.Dict[str, t.Any]) -> Params:
        """
        Some parameters reference fields, and others provide instructions
        on how to perform the query (e.g. which operator to use).

        An example of an operator parameter is {'age__operator': 'gte'}.

        You can specify how to match text fields:
        {'name__match': 'exact'}.

        Ordering is specified like: {'__order': '-name'}.

        To include readable representations of foreign keys, use:
        {'__readable': 'true'}.

        For pagination, you can override the default page size:
        {'__page_size': 15}.

        And can specify which page: {'__page': 2}.

        This method splits the params into their different types.
        """
        response = Params()

        for key, value in params.items():
            if key.endswith("__operator") and value in OPERATOR_MAP.keys():
                field_name = key.split("__operator")[0]
                response.operators[field_name] = OPERATOR_MAP[value]
                continue

            if key.endswith("__match") and value in MATCH_TYPES:
                field_name = key.split("__match")[0]
                response.match_types[field_name] = value
                continue

            if key == "__order":
                ascending = True
                if value.startswith("-"):
                    ascending = False
                    value = value[1:]
                response.order_by = OrderBy(
                    ascending=ascending, property_name=value
                )
                continue

            if key == "__page":
                try:
                    page = int(value)
                except ValueError:
                    logger.info(f"Unrecognised __page argument - {value}")
                else:
                    response.page = page
                continue

            if key == "__page_size":
                try:
                    page_size = int(value)
                except ValueError:
                    logger.info(f"Unrecognised __page_size argument - {value}")
                else:
                    response.page_size = page_size
                continue

            if key == "__readable" and value in ("true", "True", "1"):
                response.include_readable = True
                continue

            response.fields[key] = value

        return response

    def _apply_filters(self, query: Query, params: Params) -> Query:
        """
        Apply the HTTP query parameters to the Piccolo query object, then
        return it.

        Works on any queries which support `where` clauses - Select, Count,
        Objects etc.
        """
        fields = params.fields

        if fields:
            model_dict = self.pydantic_model_optional(**fields).dict()
            for field_name in fields.keys():
                value = model_dict.get(field_name, ...)
                if value is ...:
                    raise MalformedQuery(
                        f"{field_name} isn't a valid field name."
                    )
                column: Column = getattr(self.table, field_name)
                if isinstance(
                    self.table._meta.get_column_by_name(field_name),
                    (Varchar, Text),
                ):
                    match_type = params.match_types[field_name]
                    if match_type == "exact":
                        clause = column.__eq__(value)
                    elif match_type == "starts":
                        clause = column.ilike(f"{value}%")
                    elif match_type == "ends":
                        clause = column.ilike(f"%{value}")
                    else:
                        clause = column.ilike(f"%{value}%")
                    query = query.where(clause)
                else:
                    operator = params.operators[field_name]
                    query = query.where(
                        Where(column=column, value=value, operator=operator)
                    )
        return query

    async def _get_all(
        self, params: t.Optional[t.Dict[str, t.Any]] = None
    ) -> Response:
        """
        Get all rows - query parameters are used for filtering.
        """
        params = self._clean_data(params) if params else {}

        split_params = self._split_params(params)

        include_readable = split_params.include_readable
        if include_readable:
            readable_columns = [
                self.table._get_related_readable(i)
                for i in self.table._meta.foreign_key_columns
            ]
            columns = self.table._meta.columns + readable_columns
            query = self.table.select(*columns)
        else:
            query = self.table.select()

        # Apply filters
        try:
            query = self._apply_filters(query, split_params)
        except MalformedQuery as exception:
            return Response(str(exception), status_code=400)

        # Ordering
        order_by = split_params.order_by
        if order_by:
            column = getattr(self.table, order_by.property_name)
            query = query.order_by(column, ascending=order_by.ascending)
        else:
            query = query.order_by(self.table.id, ascending=False)

        # Pagination
        page_size = split_params.page_size or self.page_size
        # If the page_size is greater than max_page_size return an error
        if page_size > self.max_page_size:
            return JSONResponse(
                {
                    "error": "The page size limit has been exceeded",
                },
                status_code=403,
            )
        query = query.limit(page_size)
        page = split_params.page
        if page > 1:
            offset = page_size * (page - 1)
            query = query.offset(offset).limit(page_size)

        rows = await query.run()
        # We need to serialise it ourselves, in case there are datetime
        # fields.
        json = self.pydantic_model_plural(include_readable=include_readable)(
            rows=rows
        ).json()
        return CustomJSONResponse(json)

    ###########################################################################

    def _clean_data(self, data: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        cleaned_data: t.Dict[str, t.Any] = {}

        for key, value in data.items():
            value = None if value == "null" else value
            cleaned_data[key] = value

        return cleaned_data

    async def _post_single(self, data: t.Dict[str, t.Any]) -> Response:
        """
        Adds a single row, if the id doesn't already exist.
        """
        cleaned_data = self._clean_data(data)
        try:
            model = self.pydantic_model(**cleaned_data)
        except ValidationError as exception:
            return Response(str(exception), status_code=400)

        try:
            row = self.table(**model.dict())
            response = await row.save().run()
            # Returns the id of the inserted row.
            return JSONResponse(response, status_code=201)
        except ValueError:
            return Response("Unable to save the resource.", status_code=500)

    async def _delete_all(
        self, params: t.Optional[t.Dict[str, t.Any]] = None
    ) -> Response:
        """
        Deletes all rows - query parameters are used for filtering.
        """
        params = self._clean_data(params) if params else {}
        split_params = self._split_params(params)

        try:
            query = self._apply_filters(
                self.table.delete(force=True), split_params
            )
        except MalformedQuery as exception:
            return Response(str(exception), status_code=400)

        await query.run()
        return Response(status_code=204)

    ###########################################################################

    async def new(self, request: Request) -> CustomJSONResponse:
        """
        This endpoint is used when creating new rows in a UI. It provides
        all of the default values for a new row, but doesn't save it.
        """
        row = self.table(ignore_missing=True)
        row_dict = row.__dict__
        del row_dict["id"]

        return CustomJSONResponse(
            self.pydantic_model_optional(**row_dict).json()
        )

    ###########################################################################

    async def detail(self, request: Request) -> Response:
        """
        If a resource with a matching ID isn't found, a 404 is returned.

        This is also the case for PUT requests - we don't want the user to be
        able to specify the ID of a new resource, as this could potentially
        cause issues.
        """
        row_id = request.path_params.get("row_id", None)
        if row_id is None:
            return Response("Missing ID parameter.", status_code=404)

        if not await self.table.exists().where(self.table.id == row_id).run():
            return Response("The resource doesn't exist", status_code=404)

        if (type(row_id) is int) and row_id < 1:
            return Response(
                "The resource ID must be greater than 0", status_code=400
            )

        if request.method == "GET":
            return await self._get_single(request, row_id)
        elif request.method == "PUT":
            data = await request.json()
            return await self._put_single(row_id, data)
        elif request.method == "DELETE":
            return await self._delete_single(row_id)
        elif request.method == "PATCH":
            data = await request.json()
            return await self._patch_single(row_id, data)
        else:
            return Response(status_code=405)

    async def _get_single(self, request: Request, row_id: int) -> Response:
        """
        Returns a single row.
        """
        params = dict(request.query_params)
        split_params: Params = self._split_params(params)
        try:
            columns = self.table._meta.columns
            if split_params.include_readable:
                readable_columns = [
                    self.table._get_related_readable(i)
                    for i in self.table._meta.foreign_key_columns
                ]
                columns = columns + readable_columns

            row = (
                await self.table.select(*columns)
                .where(self.table.id == row_id)
                .first()
                .run()
            )
        except ValueError:
            return Response(
                "Unable to find a resource with that ID.", status_code=404
            )
        return CustomJSONResponse(
            self._pydantic_model_output(
                include_readable=split_params.include_readable
            )(**row).json()
        )

    async def _put_single(
        self, row_id: int, data: t.Dict[str, t.Any]
    ) -> Response:
        """
        Replaces an existing row. We don't allow new resources to be created.
        """
        cleaned_data = self._clean_data(data)

        try:
            model = self.pydantic_model(**cleaned_data)
        except ValidationError as exception:
            return Response(str(exception), status_code=400)

        cls = self.table

        values = {
            getattr(cls, key): getattr(model, key) for key in data.keys()
        }

        try:
            await cls.update(values).where(cls.id == row_id).run()
            return Response(status_code=204)
        except ValueError:
            return Response("Unable to save the resource.", status_code=500)

    async def _patch_single(
        self, row_id: int, data: t.Dict[str, t.Any]
    ) -> Response:
        """
        Patch a single row.
        """
        cleaned_data = self._clean_data(data)

        try:
            model = self.pydantic_model_optional(**cleaned_data)
        except ValidationError as exception:
            return Response(str(exception), status_code=400)

        cls = self.table

        try:
            values = {
                getattr(cls, key): getattr(model, key) for key in data.keys()
            }
        except AttributeError:
            unrecognised_keys = set(data.keys()) - set(model.dict().keys())
            return Response(
                f"Unrecognised keys - {unrecognised_keys}.", status_code=400
            )

        try:
            await cls.update(values).where(cls.id == row_id).run()
            new_row = await cls.select().where(cls.id == row_id).first().run()
            return JSONResponse(self.pydantic_model(**new_row).json())
        except ValueError:
            return Response("Unable to save the resource.", status_code=500)

    async def _delete_single(self, row_id: int) -> Response:
        """
        Deletes a single row.
        """
        try:
            await self.table.delete().where(self.table.id == row_id).run()
            return Response("Deleted the resource.", status_code=204)
        except ValueError:
            return Response("Unable to delete the resource.", status_code=500)


__all__ = ["PiccoloCRUD"]
