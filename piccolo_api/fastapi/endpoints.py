"""
Enhancing Piccolo integration with FastAPI.
"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from inspect import Signature, Parameter
import typing as t

from pydantic.main import BaseModel

try:
    from fastapi import FastAPI, Request
    from fastapi.params import Query
except ImportError:
    print(
        "Install fastapi to use this feature - "
        "pip install piccolo_api[fastapi]."
    )
from pydantic import BaseModel as PydanticBaseModel

from piccolo_api.crud.endpoints import PiccoloCRUD


ANNOTATIONS: t.DefaultDict = defaultdict(dict)


class HTTPMethod(str, Enum):
    get = "GET"
    delete = "DELETE"


@dataclass
class FastAPIKwargs:
    """
    Allows kwargs to be passed into ``FastAPIApp.add_api_route``.
    """

    all_routes: t.Dict[str, t.Any] = field(default_factory=dict)
    get: t.Dict[str, t.Any] = field(default_factory=dict)
    delete: t.Dict[str, t.Any] = field(default_factory=dict)
    post: t.Dict[str, t.Any] = field(default_factory=dict)
    put: t.Dict[str, t.Any] = field(default_factory=dict)
    patch: t.Dict[str, t.Any] = field(default_factory=dict)
    get_single: t.Dict[str, t.Any] = field(default_factory=dict)
    delete_single: t.Dict[str, t.Any] = field(default_factory=dict)

    def get_kwargs(self, endpoint_name: str) -> t.Dict[str, t.Any]:
        """
        Merges the arguments for all routes with arguments specific to the
        given route.
        """
        default = self.all_routes.copy()
        route_specific = getattr(self, endpoint_name, {})
        default.update(**route_specific)
        return default


class CountModel(BaseModel):
    count: int
    page_size: int


class FastAPIWrapper:
    """
    Wraps ``PiccoloCRUD`` so it can easily be integrated into FastAPI.
    ``PiccoloCRUD`` can be used with any ASGI framework, but this way you get
    some of the benefits of FastAPI - namely, the OpenAPI integration. You get
    more control by building your own endpoints by hand, but ``FastAPIWrapper``
    works great for getting endpoints up and running very quickly, and reducing
    boilerplate code.

    :param root_url:
        The URL to mount the endpoint at - e.g. /movies/.
    :param fastapi_app:
        The ``FastAPI`` instance you want to attach the endpoints to.
    :param piccolo_crud:
        The ``PiccoloCRUD`` instance to wrap. ``FastAPIWrapper`` will obey
        the arguments passed into ``PiccoloCRUD``, for example ``ready_only``
        and ``allow_bulk_delete``.
    :param fastapi_kwargs:
        Specifies the extra kwargs to pass to FastAPI's `add_api_route`.

    """

    def __init__(
        self,
        root_url: str,
        fastapi_app: FastAPI,
        piccolo_crud: PiccoloCRUD,
        fastapi_kwargs: FastAPIKwargs = FastAPIKwargs(),
    ):
        self.root_url = root_url
        self.fastapi_app = fastapi_app
        self.piccolo_crud = piccolo_crud
        self.fastapi_kwargs = fastapi_kwargs

        self.ModelOut = piccolo_crud.pydantic_model_output
        self.ModelIn = piccolo_crud.pydantic_model
        self.ModelOptional = piccolo_crud.pydantic_model_optional
        self.ModelPlural = piccolo_crud.pydantic_model_plural()

        self.alias = f"{piccolo_crud.table._meta.tablename}__{id(self)}"

        global ANNOTATIONS
        ANNOTATIONS[self.alias]["ModelIn"] = self.ModelIn
        ANNOTATIONS[self.alias]["ModelOut"] = self.ModelOut
        ANNOTATIONS[self.alias]["ModelOptional"] = self.ModelOptional
        ANNOTATIONS[self.alias]["ModelPlural"] = self.ModelPlural

        #######################################################################
        # Root - GET

        async def get(request: Request, **kwargs):
            """
            Returns all rows matching the given query.
            """
            return await piccolo_crud.root(request=request)

        self.modify_signature(
            endpoint=get,
            model=self.ModelOut,
            http_method=HTTPMethod.get,
            allow_ordering=True,
            allow_pagination=True,
        )

        fastapi_app.add_api_route(
            path=root_url,
            endpoint=get,
            methods=["GET"],
            response_model=self.ModelPlural,
            **fastapi_kwargs.get_kwargs("get"),
        )

        #######################################################################
        # Root - Count

        async def count(request: Request, **kwargs):
            """
            Returns the number of rows matching the given query.
            """
            return await piccolo_crud.get_count(request=request)

        self.modify_signature(
            endpoint=count, model=self.ModelOut, http_method=HTTPMethod.get
        )

        fastapi_app.add_api_route(
            path=self.join_urls(root_url, "/count/"),
            endpoint=count,
            methods=["GET"],
            response_model=CountModel,
            **fastapi_kwargs.get_kwargs("get"),
        )

        #######################################################################
        # Root - Schema

        async def schema(request: Request):
            """
            Returns the JSON schema for the given table.
            """
            return await piccolo_crud.get_schema(request=request)

        fastapi_app.add_api_route(
            path=self.join_urls(root_url, "/schema/"),
            endpoint=schema,
            methods=["GET"],
            response_model=t.Dict[str, t.Any],
            **fastapi_kwargs.get_kwargs("get"),
        )

        #######################################################################
        # Root - DELETE

        if not piccolo_crud.read_only and piccolo_crud.allow_bulk_delete:

            async def delete(request: Request, **kwargs):
                """
                Deletes all rows matching the given query.
                """
                return await piccolo_crud.root(request=request)

            self.modify_signature(
                endpoint=delete,
                model=self.ModelOut,
                http_method=HTTPMethod.delete,
            )

            fastapi_app.add_api_route(
                path=root_url,
                endpoint=delete,
                response_model=None,
                methods=["DELETE"],
                **fastapi_kwargs.get_kwargs("delete"),
            )

        #######################################################################
        # Root - POST

        if not piccolo_crud.read_only:

            async def post(request: Request, model):
                """
                Create a new row in the table.
                """
                return await piccolo_crud.root(request=request)

            post.__annotations__[
                "model"
            ] = f"ANNOTATIONS['{self.alias}']['ModelIn']"

            fastapi_app.add_api_route(
                path=root_url,
                endpoint=post,
                response_model=self.ModelOut,
                methods=["POST"],
                **fastapi_kwargs.get_kwargs("post"),
            )

        #######################################################################
        # Detail - GET

        async def get_single(row_id: int, request: Request):
            """
            Retrieve a single row from the table.
            """
            return await piccolo_crud.detail(request=request)

        fastapi_app.add_api_route(
            path=self.join_urls(root_url, "/{row_id:int}/"),
            endpoint=get_single,
            response_model=self.ModelOut,
            methods=["GET"],
            **fastapi_kwargs.get_kwargs("get_single"),
        )

        #######################################################################
        # Detail - DELETE

        if not piccolo_crud.read_only:

            async def delete_single(row_id: int, request: Request):
                """
                Delete a single row from the table.
                """
                return await piccolo_crud.detail(request=request)

            fastapi_app.add_api_route(
                path=self.join_urls(root_url, "/{row_id:int}/"),
                endpoint=delete_single,
                response_model=None,
                methods=["DELETE"],
                **fastapi_kwargs.get_kwargs("delete_single"),
            )

        #######################################################################
        # Detail - PUT

        if not piccolo_crud.read_only:

            async def put(row_id: int, request: Request, model):
                """
                Insert or update a single row.
                """
                return await piccolo_crud.detail(request=request)

            put.__annotations__[
                "model"
            ] = f"ANNOTATIONS['{self.alias}']['ModelIn']"

            fastapi_app.add_api_route(
                path=self.join_urls(root_url, "/{row_id:int}/"),
                endpoint=put,
                response_model=self.ModelOut,
                methods=["PUT"],
                **fastapi_kwargs.get_kwargs("put"),
            )

        #######################################################################
        # Detail - PATCH

        if not piccolo_crud.read_only:

            async def patch(row_id: int, request: Request, model):
                """
                Update a single row.
                """
                return await piccolo_crud.detail(request=request)

            patch.__annotations__[
                "model"
            ] = f"ANNOTATIONS['{self.alias}']['ModelOptional']"

            fastapi_app.add_api_route(
                path=self.join_urls(root_url, "/{row_id:int}/"),
                endpoint=patch,
                response_model=self.ModelOut,
                methods=["PATCH"],
                **fastapi_kwargs.get_kwargs("patch"),
            )

    @staticmethod
    def join_urls(url_1: str, url_2: str) -> str:
        """
        Combine two urls, and prevent double slashes (e.g. '/foo//bar')

        :param url_1:
            e.g. '/foo'
        :param url_2:
            e.g. '/bar
        :returns:
            e.g. '/foo/bar'

        """
        return "/".join([url_1.rstrip("/"), url_2.lstrip("/")])

    @staticmethod
    def modify_signature(
        endpoint: t.Callable,
        model: t.Type[PydanticBaseModel],
        http_method: HTTPMethod,
        allow_pagination: bool = False,
        allow_ordering: bool = False,
    ):
        """
        Modify the endpoint's signature, so FastAPI can correctly extract the
        schema from it. GET endpoints are given more filters.
        """
        parameters = [
            Parameter(
                name="request",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Request,
            ),
        ]

        for field_name, _field in model.__fields__.items():
            type_ = _field.type_
            parameters.append(
                Parameter(
                    name=field_name,
                    kind=Parameter.POSITIONAL_OR_KEYWORD,
                    default=Query(
                        default=None,
                        description=(f"Filter by the `{field_name}` column."),
                    ),
                    annotation=type_,
                ),
            )

            if type_ in (int, float, Decimal):
                parameters.append(
                    Parameter(
                        name=f"{field_name}__operator",
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        default=Query(
                            default=None,
                            description=(
                                f"Which operator to use for `{field_name}`. "
                                "The options are `e` (equals - default) `lt`, "
                                "`lte`, `gt`, and `gte`."
                            ),
                        ),
                    )
                )

            if type_ is str:
                parameters.append(
                    Parameter(
                        name=f"{field_name}__match",
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        default=Query(
                            default=None,
                            description=(
                                f"Specifies how `{field_name}` should be "
                                "matched - `contains` (default), `exact`, "
                                "`starts`, `ends`."
                            ),
                        ),
                    )
                )

        if http_method == HTTPMethod.get:
            if allow_ordering:
                parameters.extend(
                    [
                        Parameter(
                            name="__order",
                            kind=Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=str,
                            default=Query(
                                default=None,
                                description=(
                                    "Specifies which field to sort the "
                                    "results by. For example `id` to sort by "
                                    "id, and `-id` for descending."
                                ),
                            ),
                        )
                    ]
                )

            if allow_pagination:
                parameters.extend(
                    [
                        Parameter(
                            name="__page_size",
                            kind=Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=int,
                            default=Query(
                                default=None,
                                description=(
                                    "The number of results to return."
                                ),
                            ),
                        ),
                        Parameter(
                            name="__page",
                            kind=Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=int,
                            default=Query(
                                default=None,
                                description=(
                                    "Which page of results to return (default "
                                    "1)."
                                ),
                            ),
                        ),
                    ]
                )

        endpoint.__signature__ = Signature(  # type: ignore
            parameters=parameters
        )
