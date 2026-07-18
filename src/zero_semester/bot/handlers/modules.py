from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router(name="modules")


@router.callback_query(F.data.startswith("module:"))
async def open_module(callback: CallbackQuery) -> None:
    await callback.answer(
        "Прохождение карточек будет подключено следующим этапом.", show_alert=True
    )
