import jinja2
import os

from starlette.requests import Request
from starlette.responses import HTMLResponse

from piccolo_api.csrf.middleware import (
    DEFAULT_COOKIE_NAME,
    DEFAULT_HEADER_NAME,
)


ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        searchpath=os.path.join(os.path.dirname(__file__), "templates")
    )
)


def openapi_docs(
    csrf_cookie_name: str = DEFAULT_COOKIE_NAME,
    csrf_header_name: str = DEFAULT_HEADER_NAME,
):
    """
    Even though ASGI frameworks such as FastAPI and BlackSheep have endpoints
    for viewing OpenAPI / Swagger docs, out of the box they don't work well
    with some Piccolo middleware (namely CSRF middleware, which requires
    Swagger UI to add the CSRF token to the header of each API call).

    By using this endpoint instead, it will work correctly with CSRF.

    """

    def docs(request: Request):
        template = ENVIRONMENT.get_template("docs.html.jinja")
        html = template.render(
            csrf_cookie_name=csrf_cookie_name,
            csrf_header_name=csrf_header_name,
        )
        return HTMLResponse(content=html)

    return docs
