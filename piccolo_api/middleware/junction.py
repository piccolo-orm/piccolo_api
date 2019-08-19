from starlette.exceptions import HTTPException
from starlette.routing import Router
from starlette.types import Receive, Scope, Send


class JunctionMiddleware():
    """
    Allows multiple routers to be mounted at a single path - each is checked
    in turn until a match is found.
    """

    def __init__(self, *routers: Router) -> None:
        self.routers = routers

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        for router in self.routers:
            try:
                asgi = await router(scope, receive=receive, send=send)
            except HTTPException as exception:
                if exception.status_code != 404:
                    raise exception
            else:
                if getattr(asgi, 'status_code', None) == 404:
                    continue
                return

        raise HTTPException(status_code=404)
