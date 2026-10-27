from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import (
    ModuleLmsCourse,
    ModuleProgress,
    Practice,
    PracticeAttempt,
    QuizAnswer,
    SecretKey,
    SecretKeyRedemption,
)
from zero_semester.models.enums import PracticeType, ProgressStatus


@dataclass(frozen=True, slots=True)
class ModuleCompletionState:
    completed: bool
    practice_required: bool
    practice_completed: bool
    lms_required: bool
    lms_completed: bool


async def refresh_module_completion(
    session: AsyncSession,
    *,
    user_id: int,
    module_id: int,
) -> ModuleCompletionState:
    practice = await session.scalar(select(Practice).where(Practice.module_id == module_id))
    practice_completed = False
    if practice is not None:
        if practice.practice_type == PracticeType.QUIZ:
            practice_completed = bool(
                await session.scalar(
                    select(func.count())
                    .select_from(PracticeAttempt)
                    .join(QuizAnswer, QuizAnswer.attempt_id == PracticeAttempt.id)
                    .where(
                        PracticeAttempt.user_id == user_id,
                        PracticeAttempt.practice_id == practice.id,
                        PracticeAttempt.completed_at.is_not(None),
                        QuizAnswer.was_correct.is_(True),
                    )
                )
            )
        else:
            practice_completed = bool(
                await session.scalar(
                    select(func.count())
                    .select_from(PracticeAttempt)
                    .where(
                        PracticeAttempt.user_id == user_id,
                        PracticeAttempt.practice_id == practice.id,
                        PracticeAttempt.completed_at.is_not(None),
                    )
                )
            )

    lms_course_id = await session.scalar(
        select(ModuleLmsCourse.lms_course_id).where(ModuleLmsCourse.module_id == module_id)
    )
    lms_completed = False
    if lms_course_id is not None:
        lms_completed = bool(
            await session.scalar(
                select(func.count())
                .select_from(SecretKeyRedemption)
                .join(SecretKey, SecretKey.id == SecretKeyRedemption.secret_key_id)
                .where(
                    SecretKeyRedemption.user_id == user_id,
                    SecretKey.lms_course_id == lms_course_id,
                )
            )
        )

    requirements = []
    if practice is not None:
        requirements.append(practice_completed)
    if lms_course_id is not None:
        requirements.append(lms_completed)
    completed = bool(requirements) and all(requirements)

    progress = await session.scalar(
        select(ModuleProgress).where(
            ModuleProgress.user_id == user_id,
            ModuleProgress.module_id == module_id,
        )
    )
    now = datetime.now()
    if progress is None and (practice_completed or lms_completed):
        progress = ModuleProgress(
            user_id=user_id,
            module_id=module_id,
            status=ProgressStatus.COMPLETED if completed else ProgressStatus.IN_PROGRESS,
            started_at=now,
        )
        session.add(progress)
    elif progress is not None:
        progress.status = ProgressStatus.COMPLETED if completed else ProgressStatus.IN_PROGRESS
        progress.started_at = progress.started_at or now
    if progress is not None:
        progress.practice_started = progress.practice_started or practice_completed
        progress.completed_at = now if completed else None
    await session.flush()
    return ModuleCompletionState(
        completed=completed,
        practice_required=practice is not None,
        practice_completed=practice_completed,
        lms_required=lms_course_id is not None,
        lms_completed=lms_completed,
    )
