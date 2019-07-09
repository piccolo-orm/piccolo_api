from starlette.exceptions import HTTPException
from starlette.routing import Router


class JunctionMiddleware():
    """
    Allows multiple routers to be mounted at a single path - each is checked
    in turn until a match is found.
    """

    def __init__(self, *routers: Router) -> None:
        self.routers = routers

    def __call__(self, scope, receive, send):
        for router in self.routers:
            try:
                asgi = router(scope, receive=receive, send=send)
            except HTTPException as exception:
                if exception.status_code != 404:
                    raise exception
            else:
                if getattr(asgi, 'status_code', None) == 404:
                    continue
                return asgi

        raise HTTPException(status_code=404)
