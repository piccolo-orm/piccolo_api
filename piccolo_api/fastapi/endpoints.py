"""
Enhancing Piccolo integration with FastAPI.
"""

from __future__ import annotations

try:
    from fastapi import FastAPI, Request
except ImportError:
    print(
        "Install fastapi to use this feature - "
        "pip install piccolo_api[fastapi]."
    )

from piccolo_api.crud.endpoints import PiccoloCRUD


class FastAPIWrapper:
    """
    Wraps PiccoloCRUD so it can easily be integrated into FastAPI. PiccoloCRUD
    can be used with any ASGI framework, but this way you get some of the
    benefits of FastAPI - namely, the OpenAPI integration. You get more
    control by building your own endpoints by hand, but FastAPIWrapper works
    great for getting endpoints up and running very quickly, and reducing
    boilerplate code.

    :param root_url:
        The URL to mount mount the endpoint at - e.g. /movies/.
    :param fastapi_app:
        The ``FastAPI`` instance you want to attach the endpoints to.
    :param piccolo_crud:
        The ``PiccoloCRUD`` instance to wrap. ``FastAPIWrapper`` will obey
        the arguments passed into ``PiccoloCRUD``, for example ``ready_only``
        and `allow_bulk_delete`.

    """

    def join_urls(self, url_1: str, url_2: str) -> str:
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

    def __init__(
        self, root_url: str, fastapi_app: FastAPI, piccolo_crud: PiccoloCRUD
    ):
        self.root_url = root_url
        self.fastapi_app = fastapi_app
        self.piccolo_crud = piccolo_crud

        #######################################################################

        ModelOut = self.piccolo_crud.pydantic_model_output

        #######################################################################
        # Root

        self.fastapi_app.add_api_route(
            path=self.root_url,
            endpoint=self.piccolo_crud.root,
            methods=["GET"],
        )

        if not self.piccolo_crud.read_only:
            self.fastapi_app.add_api_route(
                path=self.root_url,
                endpoint=self.piccolo_crud.root,
                response_model=ModelOut,
                methods=["POST"],
            )

            if self.piccolo_crud.allow_bulk_delete:
                self.fastapi_app.add_api_route(
                    path=self.root_url,
                    endpoint=self.piccolo_crud.root,
                    response_model=None,
                    methods=["DELETE"],
                )

        #######################################################################
        # Detail

        self.fastapi_app.add_api_route(
            path=self.join_urls(self.root_url, "/{row_id:int}/"),
            endpoint=self.get_single,
            response_model=ModelOut,
            methods=["GET"],
        )

        if not self.piccolo_crud.read_only:
            self.fastapi_app.add_api_route(
                path=self.join_urls(self.root_url, "/{row_id:int}/"),
                endpoint=self.delete_single,
                response_model=None,
                methods=["DELETE"],
            )

            self.fastapi_app.add_api_route(
                path=self.join_urls(self.root_url, "/{row_id:int}/"),
                endpoint=self.put,
                response_model=ModelOut,
                methods=["PUT"],
            )

            self.fastapi_app.add_api_route(
                path=self.join_urls(self.root_url, "/{row_id:int}/"),
                endpoint=self.patch,
                response_model=ModelOut,
                methods=["PATCH"],
            )

    async def get_single(self, row_id: int, request: Request):
        return await self.piccolo_crud.detail(request=request)

    async def delete_single(self, row_id: int, request: Request):
        return await self.piccolo_crud.detail(request=request)

    async def put(self, row_id: int, request: Request):
        return await self.piccolo_crud.detail(request=request)

    async def patch(self, row_id: int, request: Request):
        return await self.piccolo_crud.detail(request=request)
