from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from zero_semester.admin.deps import DbSession
from zero_semester.security import verify_payload
from zero_semester.services.lms_links import track_lms_click

router = APIRouter()


@router.get("/go/{short_code}")
async def go_to_lms(
    short_code: str,
    session: DbSession,
    token: str | None = Query(default=None, alias="t"),
) -> RedirectResponse:
    payload = verify_payload(token) if token else None
    user_id = payload.get("user_id") if payload else None
    module_id = payload.get("module_id") if payload else None
    target_url = await track_lms_click(
        session,
        short_code=short_code,
        user_id=user_id if isinstance(user_id, int) else None,
        module_id=module_id if isinstance(module_id, int) else None,
    )
    if target_url is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    return RedirectResponse(target_url, status_code=302)
