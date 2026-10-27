from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from zero_semester.bot.keyboards import main_menu_keyboard, modules_keyboard
from zero_semester.database import session_factory
from zero_semester.repositories.users import UserRepository
from zero_semester.services.course import get_module_menu

router = Router(name="menu")


@router.message(Command("menu"))
async def menu_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu:main")
async def main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text("Главное меню", reply_markup=main_menu_keyboard())
        except TelegramBadRequest:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Главное меню", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:modules")
async def module_menu(callback: CallbackQuery) -> None:
    async with session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        if user is None:
            await callback.answer("Сначала выполни /start", show_alert=True)
            return
        items = await get_module_menu(session, user_id=user.id, school_id=user.school_id)
        await session.commit()
    if isinstance(callback.message, Message):
        text = "Выбери модуль" if items else "Опубликованных модулей пока нет."
        await callback.message.edit_text(text, reply_markup=modules_keyboard(items))
    await callback.answer()
