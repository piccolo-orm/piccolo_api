import jinja2
import os
import typing as t

from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Router

from piccolo_api.csrf.middleware import (
    DEFAULT_COOKIE_NAME,
    DEFAULT_HEADER_NAME,
)


ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        searchpath=os.path.join(os.path.dirname(__file__), "templates")
    )
)


def swagger_ui(
    schema_url: str = "/openapi.json",
    swagger_ui_title: str = "Piccolo Swagger UI",
    csrf_cookie_name: t.Optional[str] = DEFAULT_COOKIE_NAME,
    csrf_header_name: t.Optional[str] = DEFAULT_HEADER_NAME,
):
    """
    Even though ASGI frameworks such as FastAPI and BlackSheep have endpoints
    for viewing OpenAPI / Swagger docs, out of the box they don't work well
    with some Piccolo middleware (namely CSRF middleware, which requires
    Swagger UI to add the CSRF token to the header of each API call).

    By using this endpoint instead, it will work correctly with CSRF.

    **FastAPI example**

    .. code-block:: python

        from fastapi import FastAPI
        from piccolo_api.openapi.endpoints import swagger_ui

        # By setting these values to None, we disable the builtin endpoints.
        app = FastAPI(docs_url=None, redoc_url=None)

        app.mount('/docs', swagger_ui())

    :param schema_url:
        The URL to the OpenAPI schema.
    :param csrf_cookie_name:
        The name of the CSRF cookie.
    :param csrf_header_name:
        The HTTP header name which the CSRF cookie value will be added to.

    """

    # We return a router, because it's effectively a mini ASGI
    # app, which can be mounted in any ASGI app which supports mounting.
    router = Router()

    class DocsEndpoint(HTTPEndpoint):
        def get(self, request: Request):
            template = ENVIRONMENT.get_template("swagger_ui.html.jinja")
            html = template.render(
                schema_url=schema_url,
                swagger_ui_title=swagger_ui_title,
                csrf_cookie_name=csrf_cookie_name,
                csrf_header_name=csrf_header_name,
            )
            return HTMLResponse(content=html)

    class OAuthRedirectEndpoint(HTTPEndpoint):
        def get(self, request: Request):
            return get_swagger_ui_oauth2_redirect_html()

    router.add_route("/", endpoint=DocsEndpoint)
    router.add_route("/oauth2-redirect/", endpoint=OAuthRedirectEndpoint)

    return router
