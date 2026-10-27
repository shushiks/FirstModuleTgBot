from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from zero_semester.config import get_settings
from zero_semester.security import new_csrf_token

MAX_REQUEST_BYTES = 55 * 1024 * 1024


class RequestTooLargeError(Exception):
    pass


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_REQUEST_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                await JSONResponse(
                    {"detail": "Некорректный Content-Length"},
                    status_code=400,
                )(scope, receive, send)
                return

        received_bytes = 0

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_bytes:
                    raise RequestTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLargeError:
            await self._reject(scope, receive, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        await JSONResponse(
            {"detail": "Размер запроса превышает 55 МБ"},
            status_code=413,
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )(scope, receive, send)


class AdminSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        csrf_token = request.cookies.get("csrf_token") or new_csrf_token()
        request.state.csrf_token = csrf_token
        response = await call_next(request)

        settings = get_settings()
        is_secure = settings.app_env not in {"local", "test"} or request.url.scheme == "https"
        if request.cookies.get("csrf_token") != csrf_token:
            response.set_cookie(
                "csrf_token",
                csrf_token,
                httponly=True,
                secure=is_secure,
                samesite="strict",
                max_age=12 * 60 * 60,
            )

        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; media-src 'self'; "
            "script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'self'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=3600"
        else:
            response.headers["Cache-Control"] = "no-store"
        if settings.app_env == "production" and is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
