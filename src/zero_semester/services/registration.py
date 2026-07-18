from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import User
from zero_semester.models.enums import SchoolCode
from zero_semester.repositories.content import ContentRepository
from zero_semester.repositories.events import EventRepository
from zero_semester.repositories.users import UserRepository


class RegistrationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PendingRegistration:
    telegram_id: int
    time_login: str


def normalize_time_login(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise RegistrationError("Логин не может быть пустым")
    if len(normalized) > 128:
        raise RegistrationError("Логин слишком длинный")
    return normalized


async def register_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    time_login: str,
    school_code: SchoolCode,
) -> User:
    users = UserRepository(session)
    content = ContentRepository(session)

    existing = await users.get_by_telegram_id(telegram_id)
    if existing is not None:
        return existing

    normalized_login = normalize_time_login(time_login)
    if await users.get_by_time_login(normalized_login) is not None:
        raise RegistrationError("Этот Time login уже зарегистрирован")

    school = await content.get_school_by_code(school_code)
    if school is None:
        raise RegistrationError("Выбранная школа не настроена")

    user = await users.create(telegram_id, normalized_login, school.id)
    await EventRepository(session).add(
        "registration_completed", user_id=user.id, school_id=school.id
    )
    await session.commit()
    return user
