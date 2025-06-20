"""
Enhancing Piccolo integration with FastAPI.
"""

from __future__ import annotations

import datetime
from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal
from enum import Enum
from inspect import Parameter, Signature, isclass
from typing import Any, Optional, Union

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.params import Query
from pydantic import BaseModel as PydanticBaseModel
from pydantic.main import BaseModel

from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.utils.types import get_type

ANNOTATIONS: defaultdict = defaultdict(dict)


class HTTPMethod(str, Enum):
    get = "GET"
    delete = "DELETE"


class FastAPIKwargs:
    """
    Allows kwargs to be passed into ``FastAPIApp.add_api_route``.
    """

    def __init__(
        self,
        all_routes: dict[str, Any] = {},
        get: dict[str, Any] = {},
        delete: dict[str, Any] = {},
        post: dict[str, Any] = {},
        put: dict[str, Any] = {},
        patch: dict[str, Any] = {},
        get_single: dict[str, Any] = {},
        delete_single: dict[str, Any] = {},
    ):
        self.all_routes = all_routes
        self.get = get
        self.delete = delete
        self.post = post
        self.put = put
        self.patch = patch
        self.get_single = get_single
        self.delete_single = delete_single

    def get_kwargs(self, endpoint_name: str) -> dict[str, Any]:
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


class ReferenceModel(BaseModel):
    tableName: str
    columnName: str


class ReferencesModel(BaseModel):
    references: list[ReferenceModel]


class FastAPIWrapper:
    """
    Wraps ``PiccoloCRUD`` so it can easily be integrated into FastAPI.
    ``PiccoloCRUD`` can be used with any ASGI framework, but this way you get
    some of the benefits of FastAPI - namely, the OpenAPI integration. You get
    more control by building your own endpoints by hand, but ``FastAPIWrapper``
    works great for getting endpoints up and running very quickly, and reducing
    boilerplate code.

    :param root_url:
        The URL to mount the endpoint at - e.g. ``'/movies/'``.
    :param fastapi_app:
        The ``FastAPI`` instance you want to attach the endpoints to.
    :param piccolo_crud:
        The ``PiccoloCRUD`` instance to wrap. ``FastAPIWrapper`` will obey
        the arguments passed into ``PiccoloCRUD``, for example ``ready_only``
        and ``allow_bulk_delete``.
    :param fastapi_kwargs:
        Specifies the extra kwargs to pass to FastAPI's ``add_api_route``.

    """

    def __init__(
        self,
        root_url: str,
        fastapi_app: Union[FastAPI, APIRouter],
        piccolo_crud: PiccoloCRUD,
        fastapi_kwargs: Optional[FastAPIKwargs] = None,
    ):
        fastapi_kwargs = fastapi_kwargs or FastAPIKwargs()

        self.root_url = root_url
        self.fastapi_app = fastapi_app
        self.piccolo_crud = piccolo_crud
        self.fastapi_kwargs = fastapi_kwargs

        self.ModelOut = piccolo_crud.pydantic_model_output
        self.ModelIn = piccolo_crud.pydantic_model
        self.ModelOptional = piccolo_crud.pydantic_model_optional
        self.ModelPlural = piccolo_crud.pydantic_model_plural()
        self.ModelFilters = piccolo_crud.pydantic_model_filters

        self.alias = f"{piccolo_crud.table._meta.tablename}__{id(self)}"

        global ANNOTATIONS  # noqa: F824
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
            model=self.ModelFilters,
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
        # Root - IDs

        async def ids(
            request: Request,
            search: Optional[str] = None,
            limit: Optional[int] = None,
        ):
            """
            Returns a mapping of row IDs to a readable representation.
            """
            return await piccolo_crud.get_ids(request=request)

        fastapi_app.add_api_route(
            path=self.join_urls(root_url, "/ids/"),
            endpoint=ids,
            methods=["GET"],
            response_model=dict[str, str],
            **fastapi_kwargs.get_kwargs("get"),
        )

        #######################################################################
        # Root - New

        async def new(request: Request):
            """
            Returns all of the default values for a new row,
            but doesn't save it.
            """
            return await piccolo_crud.get_new(request=request)

        fastapi_app.add_api_route(
            path=self.join_urls(root_url, "/new/"),
            endpoint=new,
            methods=["GET"],
            response_model=dict[str, str],
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
            endpoint=count, model=self.ModelFilters, http_method=HTTPMethod.get
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
            response_model=dict[str, Any],
            **fastapi_kwargs.get_kwargs("get"),
        )

        #######################################################################
        # Root - References

        async def references(request: Request):
            """
            Returns a list of objects showing relationships with other tables.
            """
            return await piccolo_crud.get_references(request=request)

        fastapi_app.add_api_route(
            path=self.join_urls(root_url, "/references/"),
            endpoint=references,
            methods=["GET"],
            response_model=ReferencesModel,
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
                model=self.ModelFilters,
                http_method=HTTPMethod.delete,
            )

            fastapi_app.add_api_route(
                path=root_url,
                endpoint=delete,
                response_model=None,
                status_code=status.HTTP_204_NO_CONTENT,
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

            post.__annotations__["model"] = (
                f"ANNOTATIONS['{self.alias}']['ModelIn']"
            )

            fastapi_app.add_api_route(
                path=root_url,
                endpoint=post,
                response_model=self.ModelOut,
                status_code=status.HTTP_201_CREATED,
                methods=["POST"],
                **fastapi_kwargs.get_kwargs("post"),
            )

        #######################################################################
        # Detail - GET

        async def get_single(row_id: str, request: Request):
            """
            Retrieve a single row from the table.
            """
            return await piccolo_crud.detail(request=request)

        fastapi_app.add_api_route(
            path=self.join_urls(root_url, "/{row_id:str}/"),
            endpoint=get_single,
            response_model=self.ModelOut,
            methods=["GET"],
            **fastapi_kwargs.get_kwargs("get_single"),
        )

        #######################################################################
        # Detail - DELETE

        if not piccolo_crud.read_only:

            async def delete_single(row_id: str, request: Request):
                """
                Delete a single row from the table.
                """
                return await piccolo_crud.detail(request=request)

            fastapi_app.add_api_route(
                path=self.join_urls(root_url, "/{row_id:str}/"),
                endpoint=delete_single,
                response_model=None,
                status_code=status.HTTP_204_NO_CONTENT,
                methods=["DELETE"],
                **fastapi_kwargs.get_kwargs("delete_single"),
            )

        #######################################################################
        # Detail - PUT

        if not piccolo_crud.read_only:

            async def put(row_id: str, request: Request, model):
                """
                Insert or update a single row.
                """
                return await piccolo_crud.detail(request=request)

            put.__annotations__["model"] = (
                f"ANNOTATIONS['{self.alias}']['ModelIn']"
            )

            fastapi_app.add_api_route(
                path=self.join_urls(root_url, "/{row_id:str}/"),
                endpoint=put,
                response_model=None,
                status_code=status.HTTP_204_NO_CONTENT,
                methods=["PUT"],
                **fastapi_kwargs.get_kwargs("put"),
            )

        #######################################################################
        # Detail - PATCH

        if not piccolo_crud.read_only:

            async def patch(row_id: str, request: Request, model):
                """
                Update a single row.
                """
                return await piccolo_crud.detail(request=request)

            patch.__annotations__["model"] = (
                f"ANNOTATIONS['{self.alias}']['ModelOptional']"
            )

            fastapi_app.add_api_route(
                path=self.join_urls(root_url, "/{row_id:str}/"),
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
        endpoint: Callable,
        model: type[PydanticBaseModel],
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

        for field_name, _field in model.model_fields.items():
            annotation = _field.annotation
            assert annotation is not None
            type_ = get_type(annotation)

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

            if type_ in (
                int,
                float,
                Decimal,
                datetime.date,
                datetime.datetime,
                datetime.time,
                datetime.timedelta,
            ):
                parameters.append(
                    Parameter(
                        name=f"{field_name}__operator",
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        default=Query(
                            default=None,
                            description=(
                                f"Which operator to use for `{field_name}`. "
                                "The options are `e` (equals - default) `lt`, "
                                "`lte`, `gt`, `gte`, `ne`, `is_null`, and "
                                "`not_null`."
                            ),
                        ),
                    )
                )
            else:
                parameters.append(
                    Parameter(
                        name=f"{field_name}__operator",
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        default=Query(
                            default=None,
                            description=(
                                f"Which operator to use for `{field_name}`. "
                                "The options are `is_null`, and `not_null`."
                            ),
                        ),
                    )
                )

            # We have to check if it's a subclass of `str` for Varchar, which
            # uses Pydantics `constr` (constrained string).
            if type_ is str or (isclass(type_) and issubclass(type_, str)):
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
                        Parameter(
                            name="__visible_fields",
                            kind=Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=str,
                            default=Query(
                                default=None,
                                description=(
                                    "The fields to return. It's a comma "
                                    "separated list - for example "
                                    "'name,address'. By default all fields "
                                    "are returned."
                                ),
                            ),
                        ),
                    ]
                )

            parameters.extend(
                [
                    Parameter(
                        name="__range_header",
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=bool,
                        default=Query(
                            default=False,
                            description=(
                                "Set to 'true' to add the "
                                "Content-Range response header"
                            ),
                        ),
                    )
                ]
            )
            parameters.extend(
                [
                    Parameter(
                        name="__range_header_name",
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=str,
                        default=Query(
                            default=None,
                            description=(
                                "Specify the object name in the Content-Range "
                                "response header (defaults to the table name)."
                            ),
                        ),
                    )
                ]
            )

        endpoint.__signature__ = Signature(  # type: ignore
            parameters=parameters
        )
