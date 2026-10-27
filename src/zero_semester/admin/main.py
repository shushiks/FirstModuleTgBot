from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from zero_semester.admin.middleware import AdminSecurityMiddleware, RequestSizeLimitMiddleware
from zero_semester.admin.routes import (
    admins,
    analytics,
    auth,
    broadcasts,
    content,
    dashboard,
    keys,
    media,
    public,
    support,
    users,
)
from zero_semester.logging_config import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging("admin")
    yield

app = FastAPI(
    title="Нулевой семестр — админка",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(AdminSecurityMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)
app.include_router(auth.router)
app.include_router(public.router)
app.include_router(dashboard.router)
app.include_router(admins.router)
app.include_router(content.router)
app.include_router(keys.router)
app.include_router(media.router)
app.include_router(users.router)
app.include_router(support.router)
app.include_router(broadcasts.router)
app.include_router(analytics.router)


@app.exception_handler(StarletteHTTPException)
async def admin_http_exception_handler(
    request: Request,
    error: StarletteHTTPException,
) -> Response:
    if error.status_code == 401 and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse("/login", status_code=303)
    if error.status_code == 403 and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse("/?forbidden=1", status_code=303)
    return await http_exception_handler(request, error)


@app.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness() -> dict[str, str]:
    return {"status": "ok"}
