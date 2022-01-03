from __future__ import annotations

import itertools
import logging
import typing as t
from collections import defaultdict
from dataclasses import dataclass, field

import pydantic
from piccolo.columns import Column, Where
from piccolo.columns.column_types import Array, ForeignKey, Text, Varchar
from piccolo.columns.operators import (
    Equal,
    GreaterEqualThan,
    GreaterThan,
    LessEqualThan,
    LessThan,
)
from piccolo.columns.operators.comparison import ComparisonOperator
from piccolo.query.methods.delete import Delete
from piccolo.query.methods.select import Select
from piccolo.table import Table
from piccolo.utils.encoding import dump_json
from pydantic.error_wrappers import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Router

from piccolo_api.crud.hooks import (
    Hook,
    HookType,
    execute_delete_hooks,
    execute_patch_hooks,
    execute_post_hooks,
)

from .exceptions import MalformedQuery
from .serializers import Config, create_pydantic_model
from .validators import Validators, apply_validators

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.query.methods.count import Count
    from piccolo.query.methods.objects import Objects
    from starlette.datastructures import QueryParams
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
    operators: t.Dict[str, t.Type[ComparisonOperator]] = field(
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
    visible_fields: str = field(default="")
    range_header: bool = False
    range_header_name: str = field(default="")


def get_visible_fields_options(
    table: t.Type[Table],
    exclude_secrets: bool = False,
    max_joins: int = 0,
    prefix: str = "",
) -> t.Tuple[str, ...]:
    """
    In the schema, we tell the user which fields are allowed with the
    ``__visible_fields`` GET parameter. This function extracts the column
    names, and names of related columns too.

    :param prefix:
        Used internally by this function - the user doesn't need to set this.

    """
    fields = []

    for column in table._meta.columns:
        if exclude_secrets and column._meta.secret:
            continue

        column_name = (
            f"{prefix}.{column._meta.name}" if prefix else column._meta.name
        )
        fields.append(column_name)

        if isinstance(column, ForeignKey) and max_joins > 0:
            fields.extend(
                get_visible_fields_options(
                    table=column._foreign_key_meta.resolved_references,
                    exclude_secrets=exclude_secrets,
                    max_joins=max_joins - 1,
                    prefix=column_name,
                )
            )

    return tuple(fields)


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
        exclude_secrets: bool = True,
        validators: Validators = Validators(),
        schema_extra: t.Optional[t.Dict[str, t.Any]] = None,
        max_joins: int = 0,
        hooks: t.Optional[t.List[Hook]] = None,
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
        :param exclude_secrets:
            Any Piccolo columns with ``secret=True`` will be omitted from the
            response.
        :param validators:
            Used to provide extra validation on certain endpoints - can be
            easier than subclassing.
        :param schema_extra:
            Additional information included in the Pydantic schema.
        :param max_joins:
            Determines whether a query can request data from related tables
            using joins. For example ``/movie/?__visible_fields=name,director.name``,
            which would return:

            .. code-block:: javascript

                {
                    'rows': [
                        {
                            'name': 'Star Wars',
                            'director': {
                                'name': 'George Lucas'
                            }
                        }
                    ]
                }

            This is a very powerful feature, but before enabling it, bear in
            mind the following:

             * If set too high, it could be used maliciously to craft slow
               queries which contain lots of joins, which could slow down your
               site.
             * Don't enable it if sensitive data is contained in related
               tables, as this feature can be used to retrieve that data.

            It's best used when the data in related tables is not of a
            sensitive nature and the client is highly trusted. Consider using
            it with ``exclude_secrets=True``.

            To see which fields can be filtered in this way, you can check
            the ``visible_fields_options`` value returned by the ``/schema``
            endpoint.
        """  # noqa: E501
        self.table = table
        self.page_size = page_size
        self.read_only = read_only
        self.allow_bulk_delete = allow_bulk_delete
        self.exclude_secrets = exclude_secrets
        self.validators = validators
        self.max_joins = max_joins
        if hooks:
            self._hook_map = {
                group[0]: [hook for hook in group[1]]
                for group in itertools.groupby(hooks, lambda x: x.hook_type)
            }
        else:
            self._hook_map = None  # type: ignore

        schema_extra = schema_extra if isinstance(schema_extra, dict) else {}
        self.visible_fields_options = get_visible_fields_options(
            table=table, exclude_secrets=exclude_secrets, max_joins=max_joins
        )
        schema_extra["visible_fields_options"] = self.visible_fields_options
        self.schema_extra = schema_extra

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
            Route(path="/new/", endpoint=self.get_new, methods=["GET"]),
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
            self.table,
            model_name=f"{self.table.__name__}In",
            **self.schema_extra,
        )

    def _pydantic_model_output(
        self,
        include_readable: bool = False,
        include_columns: t.Tuple[Column, ...] = (),
        nested: t.Union[bool, t.Tuple[Column, ...]] = False,
    ) -> t.Type[pydantic.BaseModel]:
        return create_pydantic_model(
            self.table,
            include_default_columns=True,
            include_readable=include_readable,
            include_columns=include_columns,
            model_name=f"{self.table.__name__}Output",
            nested=nested,
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

    def pydantic_model_plural(
        self,
        include_readable=False,
        include_columns: t.Tuple[Column, ...] = (),
        nested: t.Union[bool, t.Tuple[Column, ...]] = False,
    ):
        """
        This is for when we want to serialise many copies of the model.
        """
        base_model: t.Any = create_pydantic_model(
            self.table,
            include_default_columns=True,
            include_readable=include_readable,
            include_columns=include_columns,
            model_name=f"{self.table.__name__}Item",
            nested=nested,
        )
        return pydantic.create_model(
            str(self.table.__name__) + "Plural",
            __config__=Config,
            rows=(t.List[base_model], None),
        )

    @apply_validators
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

    @apply_validators
    async def get_ids(self, request: Request) -> Response:
        """
        Returns all the IDs for the current table, mapped to a readable
        representation e.g. {'1': 'joebloggs'}. Used for UI, like foreign
        key selectors.

        An optional 'search' GET parameter can be used to filter the results
        returned. Also, an optional 'limit' paramter can be used to specify
        how many results should be returned, and 'offset' for basic pagination.

        """
        readable = self.table.get_readable()
        query = self.table.select().columns(
            self.table._meta.primary_key._meta.name, readable
        )

        limit = request.query_params.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                return Response(
                    "The limit must be an integer", status_code=400
                )
        else:
            limit = "ALL"

        offset = request.query_params.get("offset")
        if offset is not None:
            try:
                offset = int(offset)
            except ValueError:
                return Response(
                    "The offset must be an integer", status_code=400
                )
        else:
            offset = 0

        search_term = request.query_params.get("search")
        if search_term is not None:
            # Readable doesn't currently have a 'like' method, so we do it
            # manually.
            if self.table._meta.db.engine_type == "postgres":
                query = t.cast(
                    Select,
                    self.table.raw(
                        (
                            f"SELECT * FROM ({query.__str__()}) as subquery "
                            "WHERE subquery.readable ILIKE {} "
                            f"LIMIT {limit} OFFSET {offset}"
                        ),
                        f"%{search_term}%",
                    ),
                )
            if self.table._meta.db.engine_type == "sqlite":
                # The conversion to uppercase is necessary as SQLite doesn't
                # support ILIKE.
                sql = (
                    f"SELECT * FROM ({query.__str__()}) as subquery "
                    "WHERE UPPER(subquery.readable) LIKE {}"
                )
                if isinstance(limit, int):
                    sql += f" LIMIT {limit} OFFSET {offset}"
                query = t.cast(
                    Select, self.table.raw(sql, f"%{search_term.upper()}%")
                )
        else:
            if limit != "ALL":
                query = query.limit(limit).offset(offset)

        values = await query.run()
        return JSONResponse({i["id"]: i["readable"] for i in values})

    ###########################################################################

    @apply_validators
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

    @apply_validators
    async def get_count(self, request: Request) -> Response:
        """
        Returns the total number of rows in the table.
        """
        params = self._parse_params(request.query_params)
        split_params = self._split_params(params)

        try:
            query = self._apply_filters(self.table.count(), split_params)
        except MalformedQuery as exception:
            return Response(str(exception), status_code=400)

        count = await query.run()
        return JSONResponse({"count": count, "page_size": self.page_size})

    ###########################################################################

    def _parse_params(self, params: QueryParams) -> t.Dict[str, t.Any]:
        """
        The GET params may contain multiple values for each parameter name.
        For example:

        /tables/movie?tag=horror&tag=scifi

        Some clients, such as Axios, will use this convention:

        /tables/movie?tag[]=horror&tag[]=scifi

        This method normalises the parameter name, removing square brackets
        if present (tag[] -> tag), and will return a list of values if
        multiple are present.

        """
        params_map: t.Dict[str, t.Any] = {
            i[0]: [j[1] for j in i[1]]
            for i in itertools.groupby(params.multi_items(), lambda x: x[0])
        }

        array_columns = [
            i._meta.name
            for i in self.table._meta.columns
            if i.value_type == list
        ]

        output = {}

        for key, value in params_map.items():
            if key.endswith("[]") or key.rstrip("[]") in array_columns:
                # Is either an array, or multiple values have been passed in
                # for another field.
                key = key.rstrip("[]")
            elif len(value) == 1:
                value = value[0]

            output[key] = value

        return output

    async def root(self, request: Request) -> Response:
        if request.method == "GET":
            params = self._parse_params(request.query_params)
            return await self.get_all(request, params=params)
        elif request.method == "POST":
            data = await request.json()
            return await self.post_single(request, data)
        elif request.method == "DELETE":
            params = dict(request.query_params)
            return await self.delete_all(request, params=params)
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

        You can specify which fields want to display in rows:
        {'__visible_fields': 'id,name'}.

        You can activate the "Content-Range" response header:
        {'__range_header': True}

        If the "Content-Range" response header is enabled,
        you can configure the "plural name" used in the header:
        {'__range_header_name': 'movies'}

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

            if key == "__visible_fields":
                response.visible_fields = value
                continue

            if key == "__readable" and value in ("true", "True", "1"):
                response.include_readable = True
                continue

            if key == "__range_header":
                if value in ("true", "True", "1"):
                    response.range_header = True
                continue

            if key == "__range_header_name":
                response.range_header_name = value
                continue

            response.fields[key] = value

        return response

    def _apply_filters(
        self, query: t.Union[Select, Count, Objects, Delete], params: Params
    ) -> t.Union[Select, Count, Objects, Delete]:
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

                # Sometimes a list of values is passed in.
                values = value if isinstance(value, list) else [value]

                for value in values:
                    if isinstance(column, (Varchar, Text)):
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
                    elif isinstance(column, Array):
                        query = query.where(column.any(value))
                    else:
                        operator = params.operators[field_name]
                        query = query.where(
                            Where(
                                column=column, value=value, operator=operator
                            )
                        )
        return query

    @apply_validators
    async def get_all(
        self, request: Request, params: t.Optional[t.Dict[str, t.Any]] = None
    ) -> Response:
        """
        Get all rows - query parameters are used for filtering.
        """
        params = self._clean_data(params) if params else {}

        split_params = self._split_params(params)

        # Visible fields
        visible_fields = split_params.visible_fields
        nested: t.Union[bool, t.Tuple[Column, ...]]
        if visible_fields:
            try:
                visible_columns = self._parse_visible_fields(visible_fields)
            except ValueError as exception:
                return Response(str(exception), status_code=400)

            nested = tuple(
                i for i in visible_columns if len(i._meta.call_chain) > 0
            )
        else:
            visible_columns = self.table._meta.columns
            nested = False

        # Readable
        include_readable = split_params.include_readable
        readable_columns = (
            [
                self.table._get_related_readable(i)
                for i in visible_columns
                if isinstance(i, ForeignKey)
            ]
            if include_readable
            else []
        )

        # Build select query, and exclude secrets
        query = self.table.select(
            *visible_columns,
            *readable_columns,
            exclude_secrets=self.exclude_secrets,
        )

        # Make it nested if required
        if nested:
            query = query.output(nested=True)

        # Apply filters
        try:
            query = t.cast(Select, self._apply_filters(query, split_params))
        except MalformedQuery as exception:
            return Response(str(exception), status_code=400)

        # Ordering
        order_by = split_params.order_by
        if order_by:
            column = getattr(self.table, order_by.property_name)
            query = query.order_by(column, ascending=order_by.ascending)
        else:
            query = query.order_by(
                self.table._meta.primary_key, ascending=False
            )

        # Pagination
        page_size = split_params.page_size or self.page_size
        # If the page_size is greater than max_page_size return an error
        if page_size > self.max_page_size:
            return JSONResponse(
                {"error": "The page size limit has been exceeded"},
                status_code=403,
            )
        query = query.limit(page_size)
        page = split_params.page
        offset = 0
        if page > 1:
            offset = page_size * (page - 1)
            query = query.offset(offset).limit(page_size)

        rows = await query.run()
        headers = {}
        if split_params.range_header is True:
            plural_name = (
                split_params.range_header_name or self.table._meta.tablename
            )

            row_length = len(rows)
            if row_length == 0:
                curr_page_len = 0
            else:
                curr_page_len = row_length - 1
            curr_page_len = curr_page_len + offset
            count = await self.table.count().run()
            curr_page_string = f"{offset}-{curr_page_len}"
            headers[
                "Content-Range"
            ] = f"{plural_name} {curr_page_string}/{count}"

        # We need to serialise it ourselves, in case there are datetime
        # fields.
        json = self.pydantic_model_plural(
            include_readable=include_readable,
            include_columns=tuple(visible_columns),
            nested=nested,
        )(rows=rows).json()
        return CustomJSONResponse(json, headers=headers)

    ###########################################################################

    def _clean_data(self, data: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        cleaned_data: t.Dict[str, t.Any] = {}

        for key, value in data.items():
            value = (
                None
                if (isinstance(value, str) and value.lower() == "null")
                else value
            )
            cleaned_data[key] = value

        return cleaned_data

    @apply_validators
    async def post_single(
        self, request: Request, data: t.Dict[str, t.Any]
    ) -> Response:
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
            if self._hook_map:
                row = await execute_post_hooks(
                    hooks=self._hook_map, hook_type=HookType.pre_save, row=row
                )
            response = await row.save().run()
            json = dump_json(response)
            # Returns the id of the inserted row.
            return CustomJSONResponse(json, status_code=201)
        except ValueError:
            return Response("Unable to save the resource.", status_code=500)

    @apply_validators
    async def delete_all(
        self, request: Request, params: t.Optional[t.Dict[str, t.Any]] = None
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

    @apply_validators
    async def get_new(self, request: Request) -> CustomJSONResponse:
        """
        This endpoint is used when creating new rows in a UI. It provides
        all of the default values for a new row, but doesn't save it.
        """
        row = self.table(ignore_missing=True)
        row_dict = row.__dict__
        row_dict.pop("id", None)

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

        if (
            not await self.table.exists()
            .where(self.table._meta.primary_key == row_id)
            .run()
        ):
            return Response("The resource doesn't exist", status_code=404)

        if (type(row_id) is int) and row_id < 1:
            return Response(
                "The resource ID must be greater than 0", status_code=400
            )

        if request.method == "GET":
            return await self.get_single(request, row_id)
        elif request.method == "PUT":
            data = await request.json()
            return await self.put_single(request, row_id, data)
        elif request.method == "DELETE":
            return await self.delete_single(request, row_id)
        elif request.method == "PATCH":
            data = await request.json()
            return await self.patch_single(request, row_id, data)
        else:
            return Response(status_code=405)

    def _parse_visible_fields(self, visible_fields: str) -> t.List[Column]:
        """
        Parse the ``visible_fields`` string, and return a list of columns.

        :param visible_fields:
            A comma separated list of column names, for example ``'id,name'``.
            The presence of a full stop in the name indicates a join, for
            example ``'director.name'``.
        :raises ValueError:
            If the max join depth is exceeded, or the column name isn't
            recognised.

        """
        column_names: t.List[str] = visible_fields.split(",")
        visible_columns: t.List[Column] = []

        for column_name in column_names:
            try:
                column = self.table._meta.get_column_by_name(column_name)
            except ValueError as exception:
                raise ValueError(
                    f"{exception} - the column options are "
                    f"{self.visible_fields_options}."
                )

            if len(column._meta.call_chain) > self.max_joins:
                raise ValueError("Max join depth exceeded")
            else:
                visible_columns.append(column)

        return visible_columns

    @apply_validators
    async def get_single(self, request: Request, row_id: int) -> Response:
        """
        Returns a single row.
        """
        params = dict(request.query_params)
        split_params: Params = self._split_params(params)

        # Visible fields
        nested: t.Union[bool, t.Tuple[Column, ...]]
        visible_fields = split_params.visible_fields
        if visible_fields:
            try:
                visible_columns = self._parse_visible_fields(visible_fields)
            except ValueError as exception:
                return Response(str(exception), status_code=400)

            nested = tuple(
                i for i in visible_columns if len(i._meta.call_chain) > 0
            )
        else:
            visible_columns = self.table._meta.columns
            nested = False

        # Readable
        readable_columns = (
            [
                self.table._get_related_readable(i)
                for i in self.table._meta.foreign_key_columns
            ]
            if split_params.include_readable
            else []
        )

        query = (
            self.table.select(
                *visible_columns,
                *readable_columns,
                exclude_secrets=self.exclude_secrets,
            )
            .where(self.table._meta.primary_key == row_id)
            .first()
        )

        if nested:
            query = query.output(nested=True)

        row = await query.run()

        if not row:
            return Response(
                "Unable to find a resource with that ID.", status_code=404
            )

        return CustomJSONResponse(
            self._pydantic_model_output(
                include_readable=split_params.include_readable,
                include_columns=tuple(visible_columns),
                nested=nested,
            )(**row).json()
        )

    @apply_validators
    async def put_single(
        self, request: Request, row_id: int, data: t.Dict[str, t.Any]
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

            await cls.update(values).where(
                cls._meta.primary_key == row_id
            ).run()
            return Response(status_code=204)
        except ValueError:
            return Response("Unable to save the resource.", status_code=500)

    @apply_validators
    async def patch_single(
        self, request: Request, row_id: int, data: t.Dict[str, t.Any]
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

        if self._hook_map:
            values = await execute_patch_hooks(
                hooks=self._hook_map,
                hook_type=HookType.pre_patch,
                row_id=row_id,
                values=values,
            )

        try:
            await cls.update(values).where(
                cls._meta.primary_key == row_id
            ).run()
            new_row = (
                await cls.select(exclude_secrets=self.exclude_secrets)
                .where(cls._meta.primary_key == row_id)
                .first()
                .run()
            )
            return CustomJSONResponse(self.pydantic_model(**new_row).json())
        except ValueError:
            return Response("Unable to save the resource.", status_code=500)

    @apply_validators
    async def delete_single(self, request: Request, row_id: int) -> Response:
        """
        Deletes a single row.
        """

        if self._hook_map:
            await execute_delete_hooks(
                hooks=self._hook_map,
                hook_type=HookType.pre_delete,
                row_id=row_id,
            )

        try:
            await self.table.delete().where(
                self.table._meta.primary_key == row_id
            ).run()
            return Response(status_code=204)
        except ValueError:
            return Response("Unable to delete the resource.", status_code=500)


__all__ = ["PiccoloCRUD"]
