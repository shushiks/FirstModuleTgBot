import csv
import io

from fastapi import APIRouter, Request
from sqlalchemy import func, select
from starlette.responses import Response

from zero_semester.admin.deps import CurrentAdmin, DbSession
from zero_semester.admin.templating import render_template
from zero_semester.models import (
    Broadcast,
    CourseCompletion,
    Event,
    LmsCourse,
    Module,
    ModuleProgress,
    Practice,
    PracticeAttempt,
    QuizOption,
    School,
    SecretKeyRedemption,
    SupportTicket,
    User,
)
from zero_semester.models.enums import (
    BroadcastStatus,
    ProgressStatus,
    PublicationStatus,
    TicketStatus,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

EVENT_LABELS = {
    "registration_completed": "Пользователь завершил регистрацию",
    "lms_link_clicked": "Пользователь перешёл из бота в LMS",
    "secret_accepted": "Принят правильный ключ практики LMS",
    "secret_rejected": "Введён неверный или просроченный ключ LMS",
    "quiz_answered": "Пользователь ответил на квиз",
    "open_answered": "Сохранён ответ в дневник рефлексии",
    "poll_answered": "Пользователь проголосовал в опросе",
    "support_created": "Создано обращение в поддержку",
    "module_opened": "Пользователь открыл модуль",
}

PROPERTY_VALUE_LABELS = {
    "expired": "срок действия ключа истёк",
}


def format_event_properties(
    properties: dict[str, object],
    *,
    lms_names: dict[int, str] | None = None,
    practice_questions: dict[int, str] | None = None,
    option_texts: dict[int, str] | None = None,
) -> str:
    lms_names = lms_names or {}
    practice_questions = practice_questions or {}
    option_texts = option_texts or {}
    parts: list[str] = []
    for key, value in properties.items():
        if key == "correct":
            parts.append("Результат: верно" if value else "Результат: неверно")
            continue
        if key == "reason":
            readable_value = PROPERTY_VALUE_LABELS.get(str(value), str(value))
            parts.append(f"Причина: {readable_value}")
            continue
        if key == "lms_course_id" and type(value) is int:
            parts.append(f"LMS: {lms_names.get(value, 'курс удалён')}")
            continue
        if key == "practice_id" and type(value) is int:
            parts.append(f"Вопрос: {practice_questions.get(value, 'практика удалена')}")
            continue
        if key == "option_id" and type(value) is int:
            parts.append(f"Ответ: {option_texts.get(value, 'вариант удалён')}")
            continue
        if key == "ticket_id":
            continue
        parts.append(f"{key.replace('_', ' ').capitalize()}: {value}")
    return "; ".join(parts)


def csv_response(
    filename: str,
    headers: list[str],
    rows: list[list[object]],
) -> Response:
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([safe_csv_cell(value) for value in headers])
    writer.writerows([[safe_csv_cell(value) for value in row] for row in rows])
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def safe_csv_cell(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.lstrip(" \t\r\n")
    if stripped.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


@router.get("")
async def analytics_page(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    rows = (
        await session.execute(
            select(Event.event_name, func.count(Event.id))
            .group_by(Event.event_name)
            .order_by(func.count(Event.id).desc())
        )
    ).all()
    metrics = {
        "users": await session.scalar(select(func.count()).select_from(User)) or 0,
        "published_modules": await session.scalar(
            select(func.count()).select_from(Module).where(
                Module.status == PublicationStatus.PUBLISHED
            )
        )
        or 0,
        "open_tickets": await session.scalar(
            select(func.count()).select_from(SupportTicket).where(
                SupportTicket.status != TicketStatus.CLOSED
            )
        )
        or 0,
        "sent_broadcasts": await session.scalar(
            select(func.count()).select_from(Broadcast).where(
                Broadcast.status == BroadcastStatus.COMPLETED
            )
        )
        or 0,
    }
    return render_template(
        request,
        "analytics/index.html",
        {"admin": admin, "rows": rows, "metrics": metrics, "event_labels": EVENT_LABELS},
    )


@router.get("/export/users.csv")
async def export_users_csv(session: DbSession, _admin: CurrentAdmin) -> Response:
    modules_started = (
        select(func.count(ModuleProgress.id))
        .where(
            ModuleProgress.user_id == User.id,
            ModuleProgress.status.in_([ProgressStatus.IN_PROGRESS, ProgressStatus.COMPLETED]),
        )
        .correlate(User)
        .scalar_subquery()
    )
    modules_completed = (
        select(func.count(ModuleProgress.id))
        .where(
            ModuleProgress.user_id == User.id,
            ModuleProgress.status == ProgressStatus.COMPLETED,
        )
        .correlate(User)
        .scalar_subquery()
    )
    practice_attempts = (
        select(func.count(PracticeAttempt.id))
        .where(
            PracticeAttempt.user_id == User.id,
            PracticeAttempt.completed_at.is_not(None),
        )
        .correlate(User)
        .scalar_subquery()
    )
    secret_keys = (
        select(func.count(SecretKeyRedemption.id))
        .where(SecretKeyRedemption.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    completed_courses = (
        select(func.count(CourseCompletion.id))
        .where(CourseCompletion.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    records = (
        await session.execute(
            select(
                User,
                School.name,
                modules_started,
                modules_completed,
                practice_attempts,
                secret_keys,
                completed_courses,
            )
            .join(School, School.id == User.school_id)
            .order_by(User.created_at)
        )
    ).all()
    rows = [
        [
            user.time_login,
            user.telegram_id,
            f"@{user.telegram_username}" if user.telegram_username else "",
            school_name,
            user.created_at.isoformat(sep=" ", timespec="seconds"),
            user.last_activity_at.isoformat(sep=" ", timespec="seconds")
            if user.last_activity_at
            else "",
            "да" if user.is_blocked else "нет",
            started,
            completed,
            attempts,
            keys,
            courses,
        ]
        for user, school_name, started, completed, attempts, keys, courses in records
    ]
    return csv_response(
        "users.csv",
        [
            "time_login",
            "telegram_id",
            "telegram_username",
            "школа",
            "дата_регистрации",
            "последняя_активность",
            "заблокировал_бота",
            "модулей_начато",
            "модулей_завершено",
            "попыток_практики",
            "ключей_принято",
            "курсов_завершено",
        ],
        rows,
    )


@router.get("/export/events.csv")
async def export_events_csv(session: DbSession, _admin: CurrentAdmin) -> Response:
    records = (
        await session.execute(
            select(
                Event,
                User.time_login,
                User.telegram_username,
                School.name,
                Module.title,
            )
            .outerjoin(User, User.id == Event.user_id)
            .outerjoin(
                School,
                School.id == func.coalesce(Event.school_id, User.school_id),
            )
            .outerjoin(Module, Module.id == Event.module_id)
            .order_by(Event.occurred_at)
        )
    ).all()
    lms_ids = {
        value
        for event, *_ in records
        if type(value := (event.properties or {}).get("lms_course_id")) is int
    }
    practice_ids = {
        value
        for event, *_ in records
        if type(value := (event.properties or {}).get("practice_id")) is int
    }
    option_ids = {
        value
        for event, *_ in records
        if type(value := (event.properties or {}).get("option_id")) is int
    }
    lms_names: dict[int, str] = dict(
        (
            await session.execute(
                select(LmsCourse.id, LmsCourse.name).where(LmsCourse.id.in_(lms_ids))
            )
        ).tuples().all()
    )
    practice_questions: dict[int, str] = dict(
        (
            await session.execute(
                select(Practice.id, Practice.question).where(Practice.id.in_(practice_ids))
            )
        ).tuples().all()
    )
    option_texts: dict[int, str] = dict(
        (
            await session.execute(
                select(QuizOption.id, QuizOption.text).where(QuizOption.id.in_(option_ids))
            )
        ).tuples().all()
    )
    rows = []
    for event, time_login, telegram_username, school_name, module_title in records:
        rows.append(
            [
                event.occurred_at.isoformat(sep=" ", timespec="seconds"),
                EVENT_LABELS.get(event.event_name, event.event_name.replace("_", " ")),
                time_login or "",
                f"@{telegram_username}" if telegram_username else "",
                school_name or "",
                module_title or "",
                format_event_properties(
                    event.properties or {},
                    lms_names=lms_names,
                    practice_questions=practice_questions,
                    option_texts=option_texts,
                ),
            ]
        )
    return csv_response(
        "events.csv",
        [
            "дата",
            "событие",
            "time_login",
            "telegram",
            "школа",
            "модуль",
            "подробности",
        ],
        rows,
    )
