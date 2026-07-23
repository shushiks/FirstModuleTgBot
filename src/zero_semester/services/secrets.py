import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.config import get_settings
from zero_semester.models import CourseRun, Module, ModuleLmsCourse, SecretKey, User
from zero_semester.models.enums import PublicationStatus
from zero_semester.repositories.content import ContentRepository
from zero_semester.repositories.events import EventRepository
from zero_semester.repositories.progress import ProgressRepository
from zero_semester.services.practice import build_reflection_report_if_course_complete
from zero_semester.services.progress import refresh_module_completion


@dataclass(frozen=True, slots=True)
class SecretResult:
    accepted: bool
    already_used: bool = False
    module_completed: bool = False
    reflection_report: str | None = None


def normalize_secret(value: str) -> str:
    return value.strip().casefold()


def digest_secret(value: str) -> str:
    pepper = get_settings().lms_key_pepper.get_secret_value().encode()
    return hmac.new(pepper, normalize_secret(value).encode(), hashlib.sha256).hexdigest()


async def activate_secret_key(
    session: AsyncSession,
    *,
    lms_course_id: int,
    value: str,
    label: str,
) -> SecretKey:
    key_digest = digest_secret(value)
    existing = await session.scalar(
        select(SecretKey).where(SecretKey.key_digest == key_digest)
    )
    if existing is not None and existing.lms_course_id != lms_course_id:
        raise ValueError("Ключ уже относится к другому LMS-курсу")
    await session.execute(
        update(SecretKey)
        .where(
            SecretKey.lms_course_id == lms_course_id,
            SecretKey.is_active.is_(True),
        )
        .values(is_active=False)
    )
    if existing is None:
        existing = SecretKey(
            lms_course_id=lms_course_id,
            key_digest=key_digest,
            label=label.strip(),
            is_active=True,
        )
        session.add(existing)
    else:
        existing.label = label.strip()
        existing.is_active = True
    return existing


async def redeem_secret(session: AsyncSession, *, user_id: int, value: str) -> SecretResult:
    user = await session.get(User, user_id)
    if user is None:
        return SecretResult(accepted=False)
    content = ContentRepository(session)
    progress = ProgressRepository(session)
    events = EventRepository(session)
    secret_key = await content.get_secret_key(
        digest_secret(value),
        school_id=user.school_id,
    )

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

    module_ids = list(
        (
            await session.scalars(
                select(ModuleLmsCourse.module_id)
                .join(Module, Module.id == ModuleLmsCourse.module_id)
                .join(CourseRun, CourseRun.id == Module.course_run_id)
                .where(
                    ModuleLmsCourse.lms_course_id == secret_key.lms_course_id,
                    CourseRun.school_id == user.school_id,
                    CourseRun.status == PublicationStatus.PUBLISHED,
                    Module.status == PublicationStatus.PUBLISHED,
                )
            )
        ).all()
    )
    if not module_ids:
        await events.add("secret_rejected", user_id=user_id)
        await session.commit()
        return SecretResult(accepted=False)
    if await progress.has_secret_redemption(user_id, secret_key.id):
        states = [
            await refresh_module_completion(session, user_id=user_id, module_id=module_id)
            for module_id in module_ids
        ]
        await session.commit()
        return SecretResult(
            accepted=True,
            already_used=True,
            module_completed=any(state.completed for state in states),
        )

    await progress.redeem_secret(user_id, secret_key.id)
    await events.add(
        "secret_accepted",
        user_id=user_id,
        properties={"lms_course_id": secret_key.lms_course_id},
    )
    states = [
        await refresh_module_completion(session, user_id=user_id, module_id=module_id)
        for module_id in module_ids
    ]
    module_completed = any(state.completed for state in states)
    report = (
        await build_reflection_report_if_course_complete(session, user_id=user_id)
        if module_completed
        else None
    )
    await session.commit()
    return SecretResult(
        accepted=True,
        module_completed=module_completed,
        reflection_report=report,
    )
