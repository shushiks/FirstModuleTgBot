from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.repositories.content import ContentRepository
from zero_semester.repositories.events import EventRepository


async def track_lms_click(
    session: AsyncSession,
    *,
    short_code: str,
    user_id: int | None,
    module_id: int | None,
) -> str | None:
    course = await ContentRepository(session).get_lms_course_by_short_code(short_code)
    if course is None:
        return None
    await EventRepository(session).add(
        "lms_link_clicked",
        user_id=user_id,
        module_id=module_id,
        school_id=course.school_id,
        properties={"lms_course_id": course.id},
    )
    await session.commit()
    return course.target_url
