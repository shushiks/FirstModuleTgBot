from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import Event


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        event_name: str,
        *,
        user_id: int | None = None,
        school_id: int | None = None,
        course_run_id: int | None = None,
        module_id: int | None = None,
        properties: dict[str, object] | None = None,
    ) -> Event:
        event = Event(
            event_name=event_name,
            user_id=user_id,
            school_id=school_id,
            course_run_id=course_run_id,
            module_id=module_id,
            properties=properties or {},
        )
        self.session.add(event)
        await self.session.flush()
        return event
