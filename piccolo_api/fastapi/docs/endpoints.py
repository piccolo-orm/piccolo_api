import jinja2
import os

from starlette.requests import Request
from starlette.responses import HTMLResponse


ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        searchpath=os.path.join(os.path.dirname(__file__), "templates")
    )
)


def custom_docs(request: Request):
    """
    Override the default docs endpoint, so we can configure Swagger UI more
    (for example, passing the CSRF token as a header).
    """
    template = ENVIRONMENT.get_template("docs.html.jinja")
    html = template.render()
    return HTMLResponse(content=html)
