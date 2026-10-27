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
    token: str = Query(alias="t", min_length=20, max_length=2048),
) -> RedirectResponse:
    payload = verify_payload(token, expected_purpose="lms_click")
    user_id = payload.get("user_id") if payload else None
    module_id = payload.get("module_id") if payload else None
    signed_short_code = payload.get("short_code") if payload else None
    if (
        not isinstance(user_id, int)
        or not isinstance(module_id, int)
        or signed_short_code != short_code
    ):
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    target_url = await track_lms_click(
        session,
        short_code=short_code,
        user_id=user_id,
        module_id=module_id,
    )
    if target_url is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    return RedirectResponse(target_url, status_code=302)
