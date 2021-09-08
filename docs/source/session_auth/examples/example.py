import datetime
import typing as t

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from piccolo.engine import engine_finder
from piccolo_admin.endpoints import create_admin
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.routing import Mount, Route

from piccolo_api.crud.serializers import create_pydantic_model
from piccolo_api.csrf.middleware import CSRFMiddleware
from piccolo_api.openapi.endpoints import swagger_ui
from piccolo_api.session_auth.endpoints import session_login, session_logout
from piccolo_api.session_auth.middleware import SessionsAuthBackend

from home.tables import Task  # An example Table


# The main app with public endpoints, which will be served by Uvicorn
app = FastAPI(
    routes=[
        # If we want to use Piccolo admin:
        Mount(
            "/admin/",
            create_admin(
                tables=[Task],
                # Required when running under HTTPS:
                # allowed_hosts=['my_site.com']
            ),
        ),
        # Session Auth login:
        Mount(
            "/login/",
            session_login(redirect_to="/private/docs/"),
        ),
    ],
    docs_url=None,
    redoc_url=None,
)

# The private app with SessionAuth protected endpoints
private_app = FastAPI(
    routes=[
        Route("/logout/", session_logout(redirect_to="/")),
        # We use a custom Swagger docs endpoint instead of the default FastAPI
        # one, because this one supports CSRF middleware:
        Mount("/docs/", swagger_ui(schema_url="/private/openapi.json")),
    ],
    middleware=[
        Middleware(
            AuthenticationMiddleware,
            backend=SessionsAuthBackend(
                increase_expiry=datetime.timedelta(minutes=30)
            ),
        ),
        # CSRF middleware provides additional protection for older browsers, as
        # we're using cookies.
        Middleware(CSRFMiddleware, allow_form_param=True),
    ],
    # We disable the default Swagger docs, as we have a custom one (see above).
    docs_url=None,
    redoc_url=None,
)


# Mount our private app within the main app.
app.mount("/private/", private_app)


###############################################################################
# Example FastAPI endpoints and Pydantic models.


TaskModelIn: t.Any = create_pydantic_model(
    table=Task, model_name="TaskModelIn"
)

TaskModelOut: t.Any = create_pydantic_model(
    table=Task, include_default_columns=True, model_name="TaskModelOut"
)


@private_app.get("/tasks/", response_model=t.List[TaskModelOut])
async def tasks():
    return await Task.select().order_by(Task._meta.primary_key).run()


@private_app.post("/tasks/", response_model=TaskModelOut)
async def create_task(task: TaskModelIn):
    task = Task(**task.__dict__)
    await task.save().run()
    return TaskModelOut(**task.__dict__)


@private_app.put("/tasks/{task_id}/", response_model=TaskModelOut)
async def update_task(task_id: int, task: TaskModelIn):
    _task = (
        await Task.objects()
        .where(Task._meta.primary_key == task_id)
        .first()
        .run()
    )
    if not _task:
        return JSONResponse({}, status_code=404)

    for key, value in task.__dict__.items():
        setattr(_task, key, value)

    await _task.save().run()

    return TaskModelOut(**_task.__dict__)


@private_app.delete("/tasks/{task_id}/")
async def delete_task(task_id: int):
    task = (
        await Task.objects()
        .where(Task._meta.primary_key == task_id)
        .first()
        .run()
    )
    if not task:
        return JSONResponse({}, status_code=404)

    await task.remove().run()

    return JSONResponse({})


###############################################################################
# This is optional - it's for creating a connection pool.


@app.on_event("startup")
async def open_database_connection_pool():
    try:
        engine = engine_finder()
        await engine.start_connection_pool()
    except Exception:
        print("Unable to connect to the database")


@app.on_event("shutdown")
async def close_database_connection_pool():
    try:
        engine = engine_finder()
        await engine.close_connection_pool()
    except Exception:
        print("Unable to connect to the database")


###############################################################################

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
