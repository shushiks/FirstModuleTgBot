import asyncio
from datetime import datetime

from sqlalchemy import select

from zero_semester.database import session_factory
from zero_semester.models import CourseRun, Module, Practice, QuizOption, School
from zero_semester.models.enums import PracticeType, PublicationStatus, SchoolCode


async def seed() -> None:
    async with session_factory() as session:
        school = await session.scalar(select(School).where(School.code == SchoolCode.TECHNOLOGY))
        if school is None:
            raise SystemExit("Run migrations first")
        course_run = await session.scalar(
            select(CourseRun).where(CourseRun.school_id == school.id, CourseRun.year == 2026)
        )
        if course_run is not None:
            raise SystemExit("Demo content already exists")
        course_run = CourseRun(
            school_id=school.id,
            name="Нулевой семестр 2026 — демо",
            year=2026,
            status=PublicationStatus.PUBLISHED,
        )
        session.add(course_run)
        await session.flush()
        module = Module(
            course_run_id=course_run.id,
            title="Вуз vs школа",
            description="Демонстрационный модуль",
            position=1,
            status=PublicationStatus.PUBLISHED,
            is_required=True,
        )
        session.add(module)
        await session.flush()
        practice = Practice(
            module_id=module.id,
            practice_type=PracticeType.QUIZ,
            question="Главное отличие самостоятельной учебы?",
            explanation="В вузе студент сам отвечает за планирование и результат.",
            max_attempts=2,
        )
        session.add(practice)
        await session.flush()
        session.add_all(
            [
                QuizOption(
                    practice_id=practice.id,
                    text="Ответственность студента",
                    position=1,
                    is_correct=True,
                ),
                QuizOption(
                    practice_id=practice.id,
                    text="Отсутствие домашних заданий",
                    position=2,
                    is_correct=False,
                ),
            ]
        )
        await session.commit()
        print(f"Demo content created at {datetime.now().isoformat(timespec='seconds')}")


if __name__ == "__main__":
    asyncio.run(seed())
