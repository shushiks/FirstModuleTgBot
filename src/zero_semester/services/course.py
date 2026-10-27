from dataclasses import dataclass
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import (
    Card,
    CourseRun,
    LmsCourse,
    MediaAsset,
    Module,
    ModuleIntroMedia,
    ModuleLmsCourse,
    Post,
    Practice,
)
from zero_semester.models.enums import PracticeType, ProgressStatus, PublicationStatus
from zero_semester.repositories.content import ContentRepository
from zero_semester.repositories.progress import ProgressRepository
from zero_semester.services.progress import refresh_module_completion


@dataclass(frozen=True, slots=True)
class ModuleMenuItem:
    module_id: int
    title: str
    position: int
    status: ProgressStatus


@dataclass(frozen=True, slots=True)
class ModuleCardView:
    asset: MediaAsset
    caption: str | None


@dataclass(frozen=True, slots=True)
class ModuleContentView:
    module_id: int
    title: str
    description: str | None
    intro_asset: MediaAsset | None
    cards: tuple[ModuleCardView, ...]
    practice_id: int | None
    practice_type: PracticeType | None
    lms_short_code: str | None
    lms_button_text: str | None
    lms_target_url: str | None


async def get_module_menu(
    session: AsyncSession, *, user_id: int, school_id: int
) -> list[ModuleMenuItem]:
    modules = await ContentRepository(session).get_published_modules(school_id)
    for module in modules:
        await refresh_module_completion(session, user_id=user_id, module_id=module.id)
    statuses = await ProgressRepository(session).get_module_statuses(user_id)
    return [
        ModuleMenuItem(
            module_id=module.id,
            title=cast(str, module.title),  # type: ignore[redundant-cast]
            position=module.position,
            status=statuses.get(module.id, ProgressStatus.NOT_STARTED),
        )
        for module in modules
    ]


async def get_module_content(
    session: AsyncSession,
    *,
    module_id: int,
    school_id: int,
) -> ModuleContentView | None:
    module = await session.scalar(
        select(Module)
        .join(CourseRun, CourseRun.id == Module.course_run_id)
        .where(
            Module.id == module_id,
            CourseRun.school_id == school_id,
            Module.status == PublicationStatus.PUBLISHED,
            CourseRun.status == PublicationStatus.PUBLISHED,
        )
    )
    if module is None:
        return None
    card_rows = (
        await session.execute(
            select(Card, MediaAsset)
            .join(Post, Post.id == Card.post_id)
            .join(MediaAsset, MediaAsset.id == Card.media_asset_id)
            .where(Post.module_id == module.id)
            .order_by(Post.position, Card.position)
        )
    ).all()
    intro_asset = await session.scalar(
        select(MediaAsset)
        .join(ModuleIntroMedia, ModuleIntroMedia.media_asset_id == MediaAsset.id)
        .where(ModuleIntroMedia.module_id == module.id)
    )
    practice_row = (
        await session.execute(
            select(Practice.id, Practice.practice_type).where(Practice.module_id == module.id)
        )
    ).first()
    lms_row = (
        await session.execute(
            select(
                LmsCourse.short_code,
                ModuleLmsCourse.button_text,
                LmsCourse.target_url,
            )
            .join(ModuleLmsCourse, ModuleLmsCourse.lms_course_id == LmsCourse.id)
            .where(ModuleLmsCourse.module_id == module.id, LmsCourse.is_active.is_(True))
        )
    ).first()
    return ModuleContentView(
        module_id=module.id,
        title=cast(str, module.title),  # type: ignore[redundant-cast]
        description=cast(str | None, module.description),  # type: ignore[redundant-cast]
        intro_asset=intro_asset,
        cards=tuple(
            ModuleCardView(asset=asset, caption=cast(str | None, card.caption))
            for card, asset in card_rows
        ),
        practice_id=cast(int, practice_row[0]) if practice_row else None,
        practice_type=cast(PracticeType, practice_row[1]) if practice_row else None,
        lms_short_code=cast(str | None, lms_row[0]) if lms_row else None,
        lms_button_text=cast(str | None, lms_row[1]) if lms_row else None,
        lms_target_url=cast(str | None, lms_row[2]) if lms_row else None,
    )
