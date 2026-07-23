from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import Event, LmsCourse, Module, ModuleLmsCourse, User
from zero_semester.models.content import CourseRun
from zero_semester.models.enums import PublicationStatus
from zero_semester.repositories.events import EventRepository


async def track_lms_click(
    session: AsyncSession,
    *,
    short_code: str,
    user_id: int,
    module_id: int,
) -> str | None:
    row = (
        await session.execute(
            select(LmsCourse, User)
            .join(ModuleLmsCourse, ModuleLmsCourse.lms_course_id == LmsCourse.id)
            .join(Module, Module.id == ModuleLmsCourse.module_id)
            .join(CourseRun, CourseRun.id == Module.course_run_id)
            .join(User, User.id == user_id)
            .where(
                LmsCourse.short_code == short_code,
                LmsCourse.is_active.is_(True),
                Module.id == module_id,
                Module.status == PublicationStatus.PUBLISHED,
                CourseRun.status == PublicationStatus.PUBLISHED,
                CourseRun.school_id == User.school_id,
                LmsCourse.school_id == User.school_id,
            )
        )
    ).first()
    if row is None:
        return None
    course, user = row
    existing_event = await session.scalar(
        select(Event.id).where(
            Event.event_name == "lms_link_clicked",
            Event.user_id == user.id,
            Event.module_id == module_id,
        )
    )
    if existing_event is None:
        await EventRepository(session).add(
            "lms_link_clicked",
            user_id=user.id,
            module_id=module_id,
            school_id=course.school_id,
            properties={"lms_course_id": course.id},
        )
    await session.commit()
    return cast(str, course.target_url)
