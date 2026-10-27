from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputPollOption, Message, PollAnswer
from sqlalchemy import select

from zero_semester.bot.keyboards import main_menu_keyboard, practice_keyboard
from zero_semester.bot.states import PracticeStates
from zero_semester.database import session_factory
from zero_semester.models import QuizOption, TelegramPoll
from zero_semester.models.enums import PracticeType
from zero_semester.repositories.users import UserRepository
from zero_semester.services.practice import (
    PracticeError,
    get_practice,
    submit_open_answer,
    submit_poll_answer,
    submit_quiz_answer,
)

router = Router(name="practices")


@router.callback_query(F.data.startswith("practice:"))
async def start_practice(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return
    practice_id = int(callback.data.split(":", 1)[1])
    async with session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        practice = (
            await get_practice(session, practice_id, school_id=user.school_id)
            if user is not None
            else None
        )
    if user is None:
        await callback.answer("Сначала выполни /start", show_alert=True)
        return
    if practice is None:
        await callback.answer("Практика не найдена", show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    if practice.practice_type == PracticeType.QUIZ:
        await callback.message.answer(practice.question, reply_markup=practice_keyboard(practice))
    elif practice.practice_type == PracticeType.POLL:
        sent = await callback.message.answer_poll(
            question=practice.question,
            options=[InputPollOption(text=option.text) for option in practice.options],
            is_anonymous=False,
            allows_multiple_answers=False,
            allows_revoting=True,
        )
        if sent.poll is not None:
            async with session_factory() as session:
                user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
                if user is not None:
                    session.add(
                        TelegramPoll(
                            telegram_poll_id=sent.poll.id,
                            practice_id=practice.id,
                            user_id=user.id,
                        )
                    )
                    await session.commit()
    else:
        await state.set_state(PracticeStates.waiting_for_open_answer)
        await state.update_data(practice_id=practice.id)
        await callback.message.answer(practice.question)
    await callback.answer()


@router.callback_query(F.data.startswith("quiz:"))
async def receive_quiz_answer(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return
    _, practice_id_raw, option_id_raw = callback.data.split(":", 2)
    async with session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        if user is None:
            await callback.answer("Сначала выполни /start", show_alert=True)
            return
        try:
            correct, explanation, module_completed = await submit_quiz_answer(
                session,
                user_id=user.id,
                practice_id=int(practice_id_raw),
                option_id=int(option_id_raw),
            )
        except PracticeError as error:
            await callback.answer(str(error), show_alert=True)
            return
    result = "Верно!" if correct else "Неверно."
    if explanation:
        result = f"{result}\n\n{explanation}"
    if correct and not module_completed:
        result += "\n\nОтвет принят. Для галочки осталось пройти LMS и ввести ключ."
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(result, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("poll:"))
async def receive_poll_answer(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return
    _, practice_id_raw, option_id_raw = callback.data.split(":", 2)
    async with session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        if user is None:
            await callback.answer("Сначала выполни /start", show_alert=True)
            return
        try:
            results, module_completed, _is_first_vote = await submit_poll_answer(
                session,
                user_id=user.id,
                practice_id=int(practice_id_raw),
                option_id=int(option_id_raw),
            )
        except PracticeError as error:
            await callback.answer(str(error), show_alert=True)
            return
    await callback.message.edit_reply_markup(reply_markup=None)
    result_text = "Результаты опроса\n\n" + "\n".join(
        f"{text}: {count} ({percent}%)" for text, count, percent in results
    )
    if not module_completed:
        result_text += "\n\nГолос принят. Для галочки осталось пройти LMS и ввести ключ."
    await callback.message.answer(result_text, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.poll_answer()
async def receive_native_poll_answer(answer: PollAnswer) -> None:
    if answer.user is None or not answer.option_ids:
        return
    async with session_factory() as session:
        binding = await session.scalar(
            select(TelegramPoll).where(TelegramPoll.telegram_poll_id == answer.poll_id)
        )
        user = await UserRepository(session).get_by_telegram_id(answer.user.id)
        if binding is None or user is None or binding.user_id != user.id:
            return
        options = list(
            (
                await session.scalars(
                    select(QuizOption)
                    .where(
                        QuizOption.practice_id == binding.practice_id,
                        QuizOption.is_active.is_(True),
                    )
                    .order_by(QuizOption.position)
                )
            ).all()
        )
        selected_index = answer.option_ids[0]
        if selected_index >= len(options):
            return
        _results, module_completed, is_first_vote = await submit_poll_answer(
            session,
            user_id=user.id,
            practice_id=binding.practice_id,
            option_id=options[selected_index].id,
        )
    if is_first_vote and answer.bot is not None:
        text = "Голос принят."
        if module_completed:
            text += " Все условия модуля выполнены — в меню появилась ✅."
        else:
            text += " Для галочки осталось пройти LMS и ввести ключ."
        await answer.bot.send_message(
            answer.user.id,
            text,
            reply_markup=main_menu_keyboard(),
        )


@router.message(PracticeStates.waiting_for_open_answer, F.text)
async def receive_open_answer(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    practice_id = data.get("practice_id")
    if not isinstance(practice_id, int):
        await state.clear()
        await message.answer("Практика не найдена.", reply_markup=main_menu_keyboard())
        return
    async with session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Сначала выполни /start")
            return
        try:
            report, module_completed = await submit_open_answer(
                session,
                user_id=user.id,
                practice_id=practice_id,
                answer_text=message.text or "",
            )
        except PracticeError as error:
            await message.answer(str(error))
            return
    await state.clear()
    status_text = (
        "Ответ сохранён. Модуль пройден!"
        if module_completed
        else "Ответ сохранён. Для галочки осталось пройти LMS и ввести ключ."
    )
    await message.answer(status_text, reply_markup=main_menu_keyboard())
    if report:
        for start in range(0, len(report), 4000):
            await message.answer(report[start : start + 4000])
