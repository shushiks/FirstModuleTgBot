from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import AdminUser
from zero_semester.security import verify_password


async def authenticate_admin(
    session: AsyncSession, *, username: str, password: str
) -> AdminUser | None:
    admin: AdminUser | None = await session.scalar(
        select(AdminUser).where(AdminUser.username == username, AdminUser.is_active.is_(True))
    )
    if admin is None or not verify_password(admin.password_hash, password):
        return None
    return admin
