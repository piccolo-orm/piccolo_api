import typing as t

from piccolo.table import Table
import pydantic
from starlette.exceptions import HTTPException
from starlette.routing import Router, Route
from starlette.responses import JSONResponse
from starlette.requests import Request


class PiccoloCRUD(Router):
    """
    Wraps a Piccolo table with CRUD methods for use in a REST API.
    """

    table: Table = None

    def __init__(self, table: Table, read_only: bool = True) -> None:
        """
        :params read_only: If True, only the GET method is allowed.
        """
        self.table = table
        super().__init__(routes=[
            Route(
                path='/',
                endpoint=self.root,
                methods=['GET'] if read_only else ['GET', 'POST', 'DELETE']
            ),
            Route(
                path='/{row_id:int}/',
                endpoint=self.detail,
                methods=['GET'] if read_only else ['GET', 'PUT', 'DELETE']
            ),
            Route(
                path='/schema/',
                endpoint=self.get_schema,
                methods=['GET']
            )
        ])

    ###########################################################################

    @property
    def pydantic_model(self):
        columns = {
            i._name: (
                i.value_type,
                None
            ) for i in self.table.Meta.non_default_columns
        }
        return pydantic.create_model(
            str(self.table.__name__),
            __config__=None,
            __base__=None,
            __module__=None,
            __validators__=None,
            **columns
        )

    async def get_schema(self, request: Request):
        """
        Return a representation of the model, so a UI can generate a form.
        """
        return JSONResponse(self.pydantic_model.schema())

    ###########################################################################

    async def root(self, request: Request):
        if request.method == 'GET':
            print(request.query_params)
            params = dict(request.query_params)
            return await self._get_all(params=params)
        elif request.method == 'POST':
            data = await request.json()
            return await self._post_single(data)
        elif request.method == "DELETE":
            return await self._delete_all()

    async def _get_all(self, params: t.Optional[t.Dict] = None):
        """
        Get all rows - query parameters are used for filtering.
        """
        query = self.table.select
        if params:
            model = self.pydantic_model(**params)
            for field_name, value in model.dict().items():
                if type(value) == str:
                    query = query.where(
                        getattr(self.table, field_name).ilike(f'%{value}%')
                    )
                elif type(value) in [int, float]:
                    query = query.where(
                        getattr(self.table, field_name) == value
                    )

        values = await query.run()
        return JSONResponse(values)

    async def _post_single(self, data: t.Dict[str, t.Any]):
        """
        Adds a single row, if the id doesn't already exist.
        """
        model = self.pydantic_model(**data)

        try:
            row = self.table(**model.dict())
            response = await row.save.run()
            # Returns the id of the inserted row.
            return JSONResponse(response)
        except ValueError:
            raise HTTPException(500, 'Unable to save the row.')

        return JSONResponse(row)

    async def _delete_all(self):
        """
        Deletes all rows - query parameters are used for filtering.
        """
        # Get ids of deleted rows???
        response = await self.table.delete.run()
        return JSONResponse(response)

    ###########################################################################

    async def detail(self, request: Request):
        row_id = request.path_params.get('row_id', None)
        if not row_id:
            raise HTTPException(404, 'Missing row ID parameter.')

        if request.method == 'GET':
            return await self._get_single(row_id)
        elif request.method == 'PUT':
            data = await request.json()
            return await self._put_single(row_id, data)
        elif request.method == 'DELETE':
            return await self._delete_single(row_id)

    async def _get_single(self, row_id: int):
        """
        Returns a single row.
        """
        try:
            row = await self.table.select.where(
                self.table.id == row_id
            ).first.run()
        except ValueError:
            raise HTTPException(404, 'Unable to find a row with that ID.')

        return JSONResponse(row)

    async def _put_single(self, row_id: int, data: t.Dict[str, t.Any]):
        """
        Inserts or updates single row.
        """
        try:
            row = self.table(**data)
            row.id = row_id
            response = await row.save.run()
            # Returns the id of the inserted row.
            return JSONResponse(response)
        except ValueError:
            raise HTTPException(500, 'Unable to save the row.')

        return JSONResponse(row)

    async def _delete_single(self, row_id: int):
        """
        Deletes a single row.
        """
        try:
            response = await self.table.delete.where(
                self.table.id == row_id
            ).run()
            # Returns the id of the deleted row.
            return JSONResponse(response)
        except ValueError:
            raise HTTPException(500, 'Unable to delete the row.')


__all__ = [PiccoloCRUD]
