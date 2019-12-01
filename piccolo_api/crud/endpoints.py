from functools import lru_cache
import typing as t

from piccolo.table import Table
from piccolo.columns.column_types import ForeignKey, Varchar, Text
import pydantic
from pydantic.error_wrappers import ValidationError
from starlette.exceptions import HTTPException
from starlette.routing import Router, Route
from starlette.responses import JSONResponse, Response
from starlette.requests import Request


class CustomJSONResponse(Response):
    media_type = "application/json"


@lru_cache()
def create_pydantic_model(
    table: Table, include_default_columns=False, include_readable=False
):
    """
    Create a Pydantic model representing a table.
    """
    columns: t.Dict[str, t.Any] = {}
    piccolo_columns = (
        table._meta.columns
        if include_default_columns
        else table._meta.non_default_columns
    )
    for column in piccolo_columns:
        column_name = column._meta.name
        if type(column) == ForeignKey:
            columns[column_name] = pydantic.Field(
                default=0,
                foreign_key=True,
                to=column._foreign_key_meta.references._meta.tablename,
            )
            if include_readable:
                columns[f"{column_name}_readable"] = (str, None)
        else:
            columns[column_name] = (column.value_type, None)

    return pydantic.create_model(
        str(table.__name__),
        __config__=None,
        __base__=None,
        __module__=None,
        __validators__=None,
        **columns,
    )


class PiccoloCRUD(Router):
    """
    Wraps a Piccolo table with CRUD methods for use in a REST API.
    """

    def __init__(self, table: Table, read_only: bool = True) -> None:
        """
        :params read_only: If True, only the GET method is allowed.
        """
        self.table = table
        super().__init__(
            routes=[
                Route(
                    path="/",
                    endpoint=self.root,
                    methods=["GET"]
                    if read_only
                    else ["GET", "POST", "DELETE"],
                ),
                Route(
                    path="/{row_id:int}/",
                    endpoint=self.detail,
                    methods=["GET"] if read_only else ["GET", "PUT", "DELETE"],
                ),
                Route(
                    path="/schema/", endpoint=self.get_schema, methods=["GET"]
                ),
                Route(path="/ids/", endpoint=self.get_ids, methods=["GET"]),
            ]
        )

    ###########################################################################

    @property
    def pydantic_model(self):
        return create_pydantic_model(self.table)

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
            __config__=None,
            __base__=None,
            __module__=None,
            __validators__=None,
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

    async def _get_all(self, params: t.Optional[t.Dict] = None):
        """
        Get all rows - query parameters are used for filtering.
        """
        readable = params.get("readable", False) if params else False
        include_readable = readable and readable in ("true", "True", "1")
        if include_readable:
            del params["readable"]
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
        if params:
            model_dict = self.pydantic_model(**params).dict()
            for field_name in params.keys():
                value = model_dict[field_name]
                if isinstance(
                    self.table._meta.get_column_by_name(field_name),
                    (Varchar, Text),
                ):
                    query = query.where(
                        getattr(self.table, field_name).ilike(f"%{value}%")
                    )
                else:
                    query = query.where(
                        getattr(self.table, field_name) == value
                    )

        rows = await query.run()
        # We need to serialise it ourselves, in case there are datetime
        # fields.
        json = self.pydantic_model_plural(include_readable=include_readable)(
            rows=rows
        ).json()
        return CustomJSONResponse(json)

    async def _post_single(self, data: t.Dict[str, t.Any]):
        """
        Adds a single row, if the id doesn't already exist.
        """
        try:
            model = self.pydantic_model(**data)
        except ValidationError as exception:
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
        try:
            model = self.pydantic_model(**data)
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
