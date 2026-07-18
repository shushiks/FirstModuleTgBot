from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.repositories.content import ContentRepository
from zero_semester.repositories.events import EventRepository
from zero_semester.repositories.progress import ProgressRepository


@dataclass(frozen=True, slots=True)
class SecretResult:
    accepted: bool
    already_used: bool = False


def normalize_secret(value: str) -> str:
    return value.strip().casefold()


async def redeem_secret(session: AsyncSession, *, user_id: int, value: str) -> SecretResult:
    normalized = normalize_secret(value)
    content = ContentRepository(session)
    progress = ProgressRepository(session)
    events = EventRepository(session)
    secret_key = await content.get_secret_key(normalized)

    if secret_key is None:
        await events.add("secret_rejected", user_id=user_id)
        await session.commit()
        return SecretResult(accepted=False)

    now = datetime.now(UTC)
    if (secret_key.valid_from and now < secret_key.valid_from) or (
        secret_key.valid_until and now > secret_key.valid_until
    ):
        await events.add("secret_rejected", user_id=user_id, properties={"reason": "expired"})
        await session.commit()
        return SecretResult(accepted=False)

    if await progress.has_secret_redemption(user_id, secret_key.id):
        return SecretResult(accepted=True, already_used=True)

    await progress.redeem_secret(user_id, secret_key.id)
    await events.add(
        "secret_accepted",
        user_id=user_id,
        properties={"lms_course_id": secret_key.lms_course_id},
    )
    await session.commit()
    return SecretResult(accepted=True)
