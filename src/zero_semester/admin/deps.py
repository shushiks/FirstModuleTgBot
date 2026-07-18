from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.database import get_session
from zero_semester.models import AdminUser
from zero_semester.security import verify_payload

DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_admin(
    session: DbSession,
    admin_session: Annotated[str | None, Cookie()] = None,
) -> AdminUser:
    payload = verify_payload(admin_session) if admin_session else None
    admin_id = payload.get("admin_id") if payload else None
    if not isinstance(admin_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    admin = await session.scalar(
        select(AdminUser).where(AdminUser.id == admin_id, AdminUser.is_active.is_(True))
    )
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return admin


CurrentAdmin = Annotated[AdminUser, Depends(get_current_admin)]
