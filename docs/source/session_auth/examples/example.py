import datetime
import typing as t

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from piccolo.engine import engine_finder
from piccolo_admin.endpoints import create_admin
from piccolo_api.crud.serializers import create_pydantic_model
from piccolo_api.csrf.middleware import CSRFMiddleware
from piccolo_api.openapi.endpoints import swagger_ui
from piccolo_api.session_auth.endpoints import session_login, session_logout
from piccolo_api.session_auth.middleware import SessionsAuthBackend
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from home.endpoints import HomeEndpoint
from home.tables import Task

# public app with public endpoints
app = FastAPI(
    routes=[
        Route("/", HomeEndpoint),
        Mount(
            "/admin/",
            create_admin(
                tables=[Task],
                # Required when running under HTTPS:
                # allowed_hosts=['my_site.com']
            ),
        ),
        Mount("/static/", StaticFiles(directory="static")),
    ],
    docs_url=None,
    redoc_url=None,
)

app.mount(
    "/login/",
    session_login(redirect_to="/private/docs/"),
)

# private app with SessionAuth protected endpoints
private_app = FastAPI(
    routes=[
        Route("/logout/", session_logout(redirect_to="/")),
    ],
    middleware=[
        Middleware(
            AuthenticationMiddleware,
            backend=SessionsAuthBackend(
                increase_expiry=datetime.timedelta(minutes=30)
            ),
        ),
        Middleware(CSRFMiddleware, allow_form_param=True),
    ],
    docs_url=None,
    redoc_url=None,
)

private_app.mount("/docs/", swagger_ui(schema_url="/private/openapi.json"))

app.mount("/private/", private_app)


TaskModelIn = create_pydantic_model(table=Task, model_name="TaskModelIn")
TaskModelOut = create_pydantic_model(
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
