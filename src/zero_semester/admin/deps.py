from dataclasses import dataclass
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.database import get_session
from zero_semester.models import AdminUser
from zero_semester.models.enums import AdminRole
from zero_semester.security import csrf_tokens_match, verify_payload

DbSession = Annotated[AsyncSession, Depends(get_session)]


@dataclass(frozen=True, slots=True)
class AdminIdentity:
    id: int
    username: str
    role: AdminRole
    is_active: bool


async def get_current_admin(
    request: Request,
    session: DbSession,
    admin_session: Annotated[str | None, Cookie()] = None,
) -> AdminIdentity:
    payload = (
        verify_payload(admin_session, expected_purpose="admin_session")
        if admin_session
        else None
    )
    admin_id = payload.get("admin_id") if payload else None
    if not isinstance(admin_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    admin = await session.scalar(
        select(AdminUser).where(AdminUser.id == admin_id, AdminUser.is_active.is_(True))
    )
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        form = await request.form()
        form_token = form.get("csrf_token")
        if not csrf_tokens_match(
            request.cookies.get("csrf_token"),
            form_token if isinstance(form_token, str) else None,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Форма устарела. Обнови страницу и повтори действие.",
            )
    section_roles = {
        "/admins": {AdminRole.ADMIN},
        "/content": {AdminRole.ADMIN, AdminRole.CONTENT_MANAGER},
        "/keys": {AdminRole.ADMIN, AdminRole.CONTENT_MANAGER},
        "/media": {AdminRole.ADMIN, AdminRole.CONTENT_MANAGER},
        "/broadcasts": {AdminRole.ADMIN, AdminRole.CONTENT_MANAGER},
        "/analytics": {AdminRole.ADMIN, AdminRole.CONTENT_MANAGER},
        "/support": {AdminRole.ADMIN, AdminRole.SUPPORT},
    }
    for prefix, allowed_roles in section_roles.items():
        if request.url.path.startswith(prefix) and admin.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Для этой роли раздел недоступен",
            )
    return AdminIdentity(
        id=admin.id,
        username=admin.username,
        role=admin.role,
        is_active=admin.is_active,
    )


CurrentAdmin = Annotated[AdminIdentity, Depends(get_current_admin)]
