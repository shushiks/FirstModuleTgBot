from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import CourseRun, LmsCourse, Module, School, SecretKey
from zero_semester.models.enums import PublicationStatus, SchoolCode


class ContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_school_by_code(self, code: SchoolCode) -> School | None:
        school: School | None = await self.session.scalar(select(School).where(School.code == code))
        return school

    async def get_published_modules(self, school_id: int) -> list[Module]:
        statement = (
            select(Module)
            .join(CourseRun, CourseRun.id == Module.course_run_id)
            .where(
                CourseRun.school_id == school_id,
                CourseRun.status == PublicationStatus.PUBLISHED,
                Module.status == PublicationStatus.PUBLISHED,
            )
            .order_by(Module.position)
        )
        return list((await self.session.scalars(statement)).all())

    async def get_secret_key(self, normalized_value: str) -> SecretKey | None:
        secret_key: SecretKey | None = await self.session.scalar(
            select(SecretKey).where(
                SecretKey.normalized_value == normalized_value,
                SecretKey.is_active.is_(True),
            )
        )
        return secret_key

    async def get_lms_course_by_short_code(self, short_code: str) -> LmsCourse | None:
        course: LmsCourse | None = await self.session.scalar(
            select(LmsCourse).where(
                LmsCourse.short_code == short_code,
                LmsCourse.is_active.is_(True),
            )
        )
        return course
