from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from zero_semester.bot.keyboards import main_menu_keyboard
from zero_semester.bot.states import SecretStates
from zero_semester.database import session_factory
from zero_semester.repositories.users import UserRepository
from zero_semester.services.secrets import redeem_secret

router = Router(name="secrets")


async def ask_for_secret(message: Message, state: FSMContext) -> None:
    await state.set_state(SecretStates.waiting_for_secret)
    await message.answer("Отправь секретный ключ из LMS. Для выхода используй /menu.")


@router.message(Command("secret"))
async def secret_command(message: Message, state: FSMContext) -> None:
    await ask_for_secret(message, state)


@router.callback_query(F.data == "menu:secret")
async def secret_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if isinstance(callback.message, Message):
        await ask_for_secret(callback.message, state)
    await callback.answer()


@router.message(SecretStates.waiting_for_secret, F.text)
async def receive_secret(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    async with session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Сначала выполни /start")
            return
        result = await redeem_secret(session, user_id=user.id, value=message.text or "")
    await state.clear()
    if not result.accepted:
        await message.answer("Неверный ключ.", reply_markup=main_menu_keyboard())
    elif result.already_used:
        await message.answer("Этот ключ уже был засчитан.", reply_markup=main_menu_keyboard())
    else:
        await message.answer("Курс LMS засчитан!", reply_markup=main_menu_keyboard())
