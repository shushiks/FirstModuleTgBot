from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models.enums import ProgressStatus
from zero_semester.repositories.content import ContentRepository
from zero_semester.repositories.progress import ProgressRepository


@dataclass(frozen=True, slots=True)
class ModuleMenuItem:
    module_id: int
    title: str
    position: int
    status: ProgressStatus


async def get_module_menu(
    session: AsyncSession, *, user_id: int, school_id: int
) -> list[ModuleMenuItem]:
    modules = await ContentRepository(session).get_published_modules(school_id)
    statuses = await ProgressRepository(session).get_module_statuses(user_id)
    return [
        ModuleMenuItem(
            module_id=module.id,
            title=module.title,
            position=module.position,
            status=statuses.get(module.id, ProgressStatus.NOT_STARTED),
        )
        for module in modules
    ]
