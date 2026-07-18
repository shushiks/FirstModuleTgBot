from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from zero_semester.bot.states import SupportStates

router = Router(name="support")


async def ask_for_support(message: Message, state: FSMContext) -> None:
    await state.set_state(SupportStates.waiting_for_message)
    await message.answer(
        "Опиши вопрос и при необходимости приложи один скриншот. Для выхода — /menu."
    )


@router.message(Command("help"))
async def support_command(message: Message, state: FSMContext) -> None:
    await ask_for_support(message, state)


@router.callback_query(F.data == "menu:support")
async def support_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if isinstance(callback.message, Message):
        await ask_for_support(callback.message, state)
    await callback.answer()


@router.message(SupportStates.waiting_for_message)
async def receive_support(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Обращение принято. Сохранение и пересылка подключаются следующим этапом.")
