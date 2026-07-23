from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import (
    CourseRun,
    Module,
    ModuleProgress,
    OpenAnswer,
    Practice,
    PracticeAttempt,
    QuizAnswer,
    QuizOption,
    User,
)
from zero_semester.models.enums import PracticeType, ProgressStatus, PublicationStatus
from zero_semester.repositories.events import EventRepository
from zero_semester.services.progress import refresh_module_completion


class PracticeError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QuizOptionView:
    id: int
    text: str


@dataclass(frozen=True, slots=True)
class PracticeView:
    id: int
    module_id: int
    practice_type: PracticeType
    question: str
    explanation: str | None
    max_attempts: int
    options: tuple[QuizOptionView, ...]


def ensure_attempt_available(*, completed_attempts: int, max_attempts: int) -> int:
    if completed_attempts >= max_attempts:
        raise PracticeError("Попытки закончились")
    return completed_attempts + 1


async def _get_published_practice(
    session: AsyncSession,
    *,
    practice_id: int,
    school_id: int,
) -> Practice | None:
    practice: Practice | None = await session.scalar(
        select(Practice)
        .join(Module, Module.id == Practice.module_id)
        .join(CourseRun, CourseRun.id == Module.course_run_id)
        .where(
            Practice.id == practice_id,
            CourseRun.school_id == school_id,
            CourseRun.status == PublicationStatus.PUBLISHED,
            Module.status == PublicationStatus.PUBLISHED,
        )
    )
    return practice


async def _get_user_practice(
    session: AsyncSession,
    *,
    user_id: int,
    practice_id: int,
) -> Practice | None:
    school_id = await session.scalar(select(User.school_id).where(User.id == user_id))
    if school_id is None:
        return None
    return await _get_published_practice(
        session,
        practice_id=practice_id,
        school_id=school_id,
    )


async def get_practice(
    session: AsyncSession,
    practice_id: int,
    *,
    school_id: int,
) -> PracticeView | None:
    practice = await _get_published_practice(
        session,
        practice_id=practice_id,
        school_id=school_id,
    )
    if practice is None:
        return None
    options = list(
        (
            await session.scalars(
                select(QuizOption)
                .where(
                    QuizOption.practice_id == practice.id,
                    QuizOption.is_active.is_(True),
                )
                .order_by(QuizOption.position)
            )
        ).all()
    )
    return PracticeView(
        id=practice.id,
        module_id=practice.module_id,
        practice_type=practice.practice_type,
        question=practice.question,
        explanation=practice.explanation,
        max_attempts=practice.max_attempts,
        options=tuple(QuizOptionView(id=option.id, text=option.text) for option in options),
    )


async def get_module_practice(
    session: AsyncSession,
    module_id: int,
    *,
    school_id: int,
) -> PracticeView | None:
    practice_id = await session.scalar(select(Practice.id).where(Practice.module_id == module_id))
    return (
        await get_practice(session, practice_id, school_id=school_id)
        if practice_id is not None
        else None
    )


async def _next_attempt_number(session: AsyncSession, *, user_id: int, practice: Practice) -> int:
    completed = (
        await session.scalar(
            select(func.count())
            .select_from(PracticeAttempt)
            .where(
                PracticeAttempt.user_id == user_id,
                PracticeAttempt.practice_id == practice.id,
                PracticeAttempt.completed_at.is_not(None),
            )
        )
        or 0
    )
    return ensure_attempt_available(
        completed_attempts=completed, max_attempts=practice.max_attempts
    )


async def submit_quiz_answer(
    session: AsyncSession,
    *,
    user_id: int,
    practice_id: int,
    option_id: int,
) -> tuple[bool, str | None, bool]:
    practice = await _get_user_practice(
        session,
        user_id=user_id,
        practice_id=practice_id,
    )
    option = await session.get(QuizOption, option_id)
    if (
        practice is None
        or practice.practice_type != PracticeType.QUIZ
        or option is None
        or option.practice_id != practice.id
        or not option.is_active
    ):
        raise PracticeError("Квиз не найден")
    attempt_number = await _next_attempt_number(session, user_id=user_id, practice=practice)
    attempt = PracticeAttempt(
        user_id=user_id,
        practice_id=practice.id,
        attempt_number=attempt_number,
        completed_at=datetime.now(),
    )
    session.add(attempt)
    await session.flush()
    session.add(
        QuizAnswer(attempt_id=attempt.id, option_id=option.id, was_correct=option.is_correct)
    )
    await session.flush()
    completion = await refresh_module_completion(
        session, user_id=user_id, module_id=practice.module_id
    )
    await EventRepository(session).add(
        "quiz_answered",
        user_id=user_id,
        module_id=practice.module_id,
        properties={"practice_id": practice.id, "correct": option.is_correct},
    )
    await session.commit()
    return option.is_correct, practice.explanation, completion.completed


async def submit_open_answer(
    session: AsyncSession,
    *,
    user_id: int,
    practice_id: int,
    answer_text: str,
) -> tuple[str | None, bool]:
    practice = await _get_user_practice(
        session,
        user_id=user_id,
        practice_id=practice_id,
    )
    answer = answer_text.strip()
    if practice is None or practice.practice_type != PracticeType.OPEN_QUESTION:
        raise PracticeError("Открытый вопрос не найден")
    if not answer:
        raise PracticeError("Ответ не может быть пустым")
    attempt_number = await _next_attempt_number(session, user_id=user_id, practice=practice)
    attempt = PracticeAttempt(
        user_id=user_id,
        practice_id=practice.id,
        attempt_number=attempt_number,
        completed_at=datetime.now(),
    )
    session.add(attempt)
    await session.flush()
    session.add(OpenAnswer(attempt_id=attempt.id, answer_text=answer))
    await session.flush()
    completion = await refresh_module_completion(
        session, user_id=user_id, module_id=practice.module_id
    )
    await EventRepository(session).add(
        "open_answered",
        user_id=user_id,
        module_id=practice.module_id,
        properties={"practice_id": practice.id},
    )
    await session.flush()
    report = (
        await build_reflection_report_if_course_complete(session, user_id=user_id)
        if completion.completed
        else None
    )
    await session.commit()
    return report, completion.completed


async def submit_poll_answer(
    session: AsyncSession,
    *,
    user_id: int,
    practice_id: int,
    option_id: int,
) -> tuple[tuple[tuple[str, int, int], ...], bool, bool]:
    practice = await _get_user_practice(
        session,
        user_id=user_id,
        practice_id=practice_id,
    )
    option = await session.get(QuizOption, option_id)
    if (
        practice is None
        or practice.practice_type != PracticeType.POLL
        or option is None
        or option.practice_id != practice.id
        or not option.is_active
    ):
        raise PracticeError("Опрос не найден")
    existing = await session.scalar(
        select(PracticeAttempt)
        .join(QuizAnswer, QuizAnswer.attempt_id == PracticeAttempt.id)
        .where(
            PracticeAttempt.user_id == user_id,
            PracticeAttempt.practice_id == practice.id,
        )
        .order_by(PracticeAttempt.attempt_number)
    )
    is_first_vote = existing is None
    if existing is None:
        attempt = PracticeAttempt(
            user_id=user_id,
            practice_id=practice.id,
            attempt_number=1,
            completed_at=datetime.now(),
        )
        session.add(attempt)
        await session.flush()
        session.add(QuizAnswer(attempt_id=attempt.id, option_id=option.id, was_correct=False))
    else:
        answer = await session.get(QuizAnswer, existing.id)
        if answer is not None:
            answer.option_id = option.id
    await session.flush()
    completion = await refresh_module_completion(
        session, user_id=user_id, module_id=practice.module_id
    )
    await EventRepository(session).add(
        "poll_answered",
        user_id=user_id,
        module_id=practice.module_id,
        properties={"practice_id": practice.id, "option_id": option.id},
    )
    await session.flush()
    rows = (
        await session.execute(
            select(QuizOption.text, func.count(QuizAnswer.attempt_id))
            .outerjoin(QuizAnswer, QuizAnswer.option_id == QuizOption.id)
            .where(
                QuizOption.practice_id == practice.id,
                QuizOption.is_active.is_(True),
            )
            .group_by(QuizOption.id)
            .order_by(QuizOption.position)
        )
    ).all()
    total = sum(count for _, count in rows)
    await session.commit()
    return (
        tuple((text, count, round(count * 100 / total) if total else 0) for text, count in rows),
        completion.completed,
        is_first_vote,
    )


async def build_reflection_report_if_course_complete(
    session: AsyncSession,
    *,
    user_id: int,
) -> str | None:
    user = await session.get(User, user_id)
    if user is None:
        return None
    course_run = await session.scalar(
        select(CourseRun)
        .where(
            CourseRun.school_id == user.school_id,
            CourseRun.status == PublicationStatus.PUBLISHED,
        )
        .order_by(CourseRun.year.desc())
    )
    if course_run is None:
        return None
    required_module_ids = list(
        (
            await session.scalars(
                select(Module.id).where(
                    Module.course_run_id == course_run.id,
                    Module.status == PublicationStatus.PUBLISHED,
                    Module.is_required.is_(True),
                )
            )
        ).all()
    )
    if not required_module_ids:
        return None
    completed = (
        await session.scalar(
            select(func.count(ModuleProgress.id)).where(
                ModuleProgress.user_id == user_id,
                ModuleProgress.module_id.in_(required_module_ids),
                ModuleProgress.status == ProgressStatus.COMPLETED,
            )
        )
        or 0
    )
    if completed < len(required_module_ids):
        return None
    answers = (
        await session.execute(
            select(
                Module.position,
                Module.title,
                Practice.question,
                OpenAnswer.answer_text,
                PracticeAttempt.created_at,
            )
            .join(Practice, Practice.module_id == Module.id)
            .join(PracticeAttempt, PracticeAttempt.practice_id == Practice.id)
            .join(OpenAnswer, OpenAnswer.attempt_id == PracticeAttempt.id)
            .where(
                Module.course_run_id == course_run.id,
                PracticeAttempt.user_id == user_id,
            )
            .order_by(Module.position, PracticeAttempt.created_at)
        )
    ).all()
    latest: dict[tuple[int, str, str], str] = {}
    for position, module_title, question, answer, _created_at in answers:
        latest[(position, module_title, question)] = answer
    if not latest:
        return None
    sections = ["Твой дневник рефлексии"]
    for (_position, module_title, question), answer in latest.items():
        sections.append(f"{module_title}\n{question}\nОтвет: {answer}")
    return "\n\n".join(sections)
