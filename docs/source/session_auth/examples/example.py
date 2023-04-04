import datetime
import typing as t

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from home.tables import Movie  # An example Table
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

# The main app with public endpoints, which will be served by Uvicorn
app = FastAPI(
    routes=[
        # If we want to use Piccolo admin:
        Mount(
            "/admin/",
            create_admin(
                tables=[Movie],
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


MovieModelIn: t.Any = create_pydantic_model(
    table=Movie, model_name="MovieModelIn"
)

MovieModelOut: t.Any = create_pydantic_model(
    table=Movie, include_default_columns=True, model_name="MovieModelOut"
)


@private_app.get("/movies/", response_model=t.List[MovieModelOut])
async def movies():
    return await Movie.select().order_by(Movie._meta.primary_key)


@private_app.post("/movies/", response_model=MovieModelOut)
async def create_movie(movie_model: MovieModelIn):
    movie = Movie(**movie_model.dict())
    await movie.save()
    return MovieModelOut(**movie.to_dict())


@private_app.put("/movies/{movie_id}/", response_model=MovieModelOut)
async def update_movie(movie_id: int, movie_model: MovieModelIn):
    movie = await Movie.objects().get(Movie._meta.primary_key == movie_id)
    if not movie:
        return JSONResponse({}, status_code=404)

    for key, value in movie_model.dict().items():
        setattr(movie, key, value)

    await movie.save().run()

    return MovieModelOut(**movie.to_dict())


@private_app.delete("/movies/{movie_id}/")
async def delete_movie(movie_id: int):
    movie = (
        await Movie.objects()
        .where(Movie._meta.primary_key == movie_id)
        .first()
    )
    if not movie:
        return JSONResponse({}, status_code=404)

    await movie.remove()

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
