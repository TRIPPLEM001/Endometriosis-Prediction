"""
main.py

FastAPI application entry point: settings, model loading at startup, CORS,
error handling, the auth and screening routes, and a liveness endpoint.
Export and delete routes live under /account and /screenings.

Run locally:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import account, auth, screenings
from app.core.config import get_settings
from app.services.model_registry import load_registry

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the models once. If any artifact is missing or inconsistent this
    # raises, and the app refuses to start rather than fail on the first request.
    app.state.registry = load_registry(settings.artifacts_dir)
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    # Interactive docs are handy in development but are not exposed in production.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(screenings.router)
app.include_router(account.router)


@app.middleware("http")
async def no_store(request: Request, call_next):
    # Responses can contain health answers and reports, so browsers and
    # intermediate proxies are told not to keep copies.
    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default 422 echoes back the submitted value of every invalid
    # field ("input"). For passwords and health answers that would put
    # sensitive data into responses and any logs that record them, so only
    # where and why a field failed is returned.
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "model_validated": settings.model_validated,
    }
