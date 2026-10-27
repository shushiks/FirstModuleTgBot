from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from zero_semester.bot.keyboards import main_menu_keyboard, school_keyboard
from zero_semester.bot.states import RegistrationStates
from zero_semester.database import session_factory
from zero_semester.models.enums import SchoolCode
from zero_semester.repositories.users import UserRepository
from zero_semester.services.registration import (
    RegistrationError,
    normalize_time_login,
    register_user,
)

router = Router(name="start")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await state.clear()
    async with session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user is not None:
        await message.answer(
            f"С возвращением, {message.from_user.first_name}!", reply_markup=main_menu_keyboard()
        )
        return
    await state.set_state(RegistrationStates.waiting_for_login)
    await message.answer(f"Привет, {message.from_user.first_name}! Введи свой Time login.")


@router.message(RegistrationStates.waiting_for_login, F.text)
async def receive_login(message: Message, state: FSMContext) -> None:
    try:
        login = normalize_time_login(message.text or "")
    except RegistrationError as error:
        await message.answer(str(error))
        return
    await state.update_data(time_login=login)
    await state.set_state(RegistrationStates.waiting_for_school)
    await message.answer(
        "Выбери школу. После регистрации ее меняет поддержка.", reply_markup=school_keyboard()
    )


@router.callback_query(RegistrationStates.waiting_for_school, F.data.startswith("school:"))
async def receive_school(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or callback.data is None:
        return
    code = SchoolCode(callback.data.split(":", 1)[1])
    data = await state.get_data()
    try:
        async with session_factory() as session:
            await register_user(
                session,
                telegram_id=callback.from_user.id,
                telegram_username=callback.from_user.username,
                time_login=str(data["time_login"]),
                school_code=code,
            )
    except RegistrationError as error:
        await callback.answer(str(error), show_alert=True)
        return
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Регистрация завершена.", reply_markup=main_menu_keyboard()
        )
    await callback.answer()
