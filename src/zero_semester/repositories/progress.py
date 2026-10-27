from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import ModuleProgress, SecretKeyRedemption
from zero_semester.models.enums import ProgressStatus


class ProgressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_module_statuses(self, user_id: int) -> dict[int, ProgressStatus]:
        rows = await self.session.execute(
            select(ModuleProgress.module_id, ModuleProgress.status).where(
                ModuleProgress.user_id == user_id
            )
        )
        return dict(rows.tuples().all())

    async def has_secret_redemption(self, user_id: int, secret_key_id: int) -> bool:
        statement = (
            select(func.count())
            .select_from(SecretKeyRedemption)
            .where(
                SecretKeyRedemption.user_id == user_id,
                SecretKeyRedemption.secret_key_id == secret_key_id,
            )
        )
        return bool(await self.session.scalar(statement))

    async def redeem_secret(self, user_id: int, secret_key_id: int) -> SecretKeyRedemption:
        redemption = SecretKeyRedemption(user_id=user_id, secret_key_id=secret_key_id)
        self.session.add(redemption)
        await self.session.flush()
        return redemption

    async def mark_module_started(self, user_id: int, module_id: int) -> None:
        progress = await self.session.scalar(
            select(ModuleProgress).where(
                ModuleProgress.user_id == user_id,
                ModuleProgress.module_id == module_id,
            )
        )
        if progress is None:
            self.session.add(
                ModuleProgress(
                    user_id=user_id,
                    module_id=module_id,
                    status=ProgressStatus.IN_PROGRESS,
                    started_at=datetime.now(),
                )
            )
        elif progress.status == ProgressStatus.NOT_STARTED:
            progress.status = ProgressStatus.IN_PROGRESS
            progress.started_at = progress.started_at or datetime.now()
        await self.session.flush()
