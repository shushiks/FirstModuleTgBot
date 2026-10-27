from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        user: User | None = await self.session.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )
        return user

    async def get_by_time_login(self, time_login: str) -> User | None:
        user: User | None = await self.session.scalar(
            select(User).where(User.time_login == time_login)
        )
        return user

    async def create(
        self,
        telegram_id: int,
        time_login: str,
        school_id: int,
        telegram_username: str | None = None,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            time_login=time_login,
            school_id=school_id,
            last_activity_at=datetime.now(),
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_school(self, user: User, school_id: int) -> None:
        user.school_id = school_id
        await self.session.flush()

    async def set_telegram_username(self, user: User, username: str | None) -> None:
        user.telegram_username = username
        await self.session.flush()
