from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

ADMIN_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=ADMIN_DIR / "templates")


def render_template(
    request: Request,
    name: str,
    context: dict[str, Any] | None = None,
    *,
    status_code: int = 200,
) -> HTMLResponse:
    template_context = dict(context or {})
    template_context["csrf_token"] = request.state.csrf_token
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=template_context,
        status_code=status_code,
    )
