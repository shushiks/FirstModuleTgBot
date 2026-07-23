import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from zero_semester.bot.keyboards import (
    main_menu_keyboard,
    support_group_close_keyboard,
)
from zero_semester.bot.states import SupportStates
from zero_semester.config import get_settings
from zero_semester.database import session_factory
from zero_semester.models import SupportMessage, SupportTicket, User
from zero_semester.models.enums import TicketStatus
from zero_semester.repositories.users import UserRepository
from zero_semester.services.support import add_support_message, create_support_ticket

router = Router(name="support")
logger = logging.getLogger(__name__)


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
    if message.from_user is None:
        return
    if message.text is None and not message.photo:
        await message.answer(
            "Можно отправить текст или один скриншот. Голосовые и видео не принимаются."
        )
        return
    support_chat_id = get_settings().telegram_support_chat_id
    if support_chat_id is None:
        await message.answer("Поддержка временно не настроена. Попробуй позже.")
        return
    bot = message.bot
    if bot is None:
        await message.answer("Не удалось отправить обращение. Попробуй позже.")
        return
    async with session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Сначала выполни /start")
            return
        telegram_contact = (
            f"@{message.from_user.username}"
            if message.from_user.username
            else f"{message.from_user.full_name} (ID: {message.from_user.id})"
        )
        state_data = await state.get_data()
        ticket_id = state_data.get("ticket_id")
        ticket = await session.get(SupportTicket, ticket_id) if isinstance(ticket_id, int) else None
        if ticket is None:
            ticket = await session.scalar(
                select(SupportTicket)
                .where(
                    SupportTicket.user_id == user.id,
                    SupportTicket.status != TicketStatus.CLOSED,
                )
                .order_by(SupportTicket.created_at.desc())
                .limit(1)
            )
            if ticket is not None:
                await state.update_data(ticket_id=ticket.id)
        if ticket is not None and ticket.status == TicketStatus.CLOSED:
            await state.clear()
            await message.answer(
                "Это обращение уже закрыто поддержкой. Если появился новый вопрос, "
                "открой «Помощь» ещё раз.",
                reply_markup=main_menu_keyboard(),
            )
            return
        support_header = (
            f"Дополнение к обращению #{ticket.id}"
            if ticket is not None
            else (
                f"Новое обращение\nTime login: {user.time_login}\n"
                f"Telegram: {telegram_contact}"
            )
        )
        support_text = message.text or message.caption or "Скриншот без комментария"
        try:
            if message.photo:
                delivered = await bot.send_photo(
                    support_chat_id,
                    photo=message.photo[-1].file_id,
                    caption=f"{support_header}\n\n{support_text}"[:1024],
                    reply_to_message_id=(
                        ticket.support_chat_message_id if ticket is not None else None
                    ),
                )
            else:
                delivered = await bot.send_message(
                    support_chat_id,
                    f"{support_header}\n\n{support_text}"[:4096],
                    reply_to_message_id=(
                        ticket.support_chat_message_id if ticket is not None else None
                    ),
                )
        except TelegramAPIError:
            logger.exception("Failed to deliver support request to chat %s", support_chat_id)
            await message.answer(
                "Не удалось передать обращение в поддержку. Мы уже видим проблему; "
                "попробуй позже."
            )
            return
        if ticket is None:
            ticket = await create_support_ticket(
                session,
                user_id=user.id,
                category="general",
                text=message.text or message.caption,
                support_chat_message_id=delivered.message_id,
            )
            await state.update_data(ticket_id=ticket.id)
            try:
                await bot.edit_message_reply_markup(
                    chat_id=support_chat_id,
                    message_id=delivered.message_id,
                    reply_markup=support_group_close_keyboard(ticket.id),
                )
            except TelegramAPIError:
                logger.exception("Failed to add close button for ticket %s", ticket.id)
            response_text = (
                "Обращение принято. Можешь дописывать сообщения сюда без повторной /help. "
                "Для выхода — /menu."
            )
        else:
            await add_support_message(
                session,
                ticket=ticket,
                text=message.text or message.caption,
                support_chat_message_id=delivered.message_id,
            )
            response_text = "Сообщение добавлено в обращение. Для выхода — /menu."
    await message.answer(response_text)


@router.callback_query(F.data.startswith("support:group_close:"))
async def close_support_from_group(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return
    support_chat_id = get_settings().telegram_support_chat_id
    if support_chat_id is None or callback.message.chat.id != support_chat_id:
        await callback.answer("Кнопка доступна только группе поддержки", show_alert=True)
        return
    ticket_id = int(callback.data.rsplit(":", 1)[1])
    async with session_factory() as session:
        ticket = await session.get(SupportTicket, ticket_id)
        if ticket is None:
            await callback.answer("Обращение не найдено", show_alert=True)
            return
        user = await session.get(User, ticket.user_id)
        support_message_ids = list(
            (
                await session.scalars(
                    select(SupportMessage.support_chat_message_id).where(
                        SupportMessage.ticket_id == ticket.id,
                        SupportMessage.sender_type == "user",
                        SupportMessage.support_chat_message_id.is_not(None),
                    )
                )
            ).all()
        )
        ticket.status = TicketStatus.CLOSED
        ticket.closed_at = datetime.now()
        await session.commit()
    bot = callback.bot
    if bot is not None:
        message_ids = {
            message_id
            for message_id in [ticket.support_chat_message_id, *support_message_ids]
            if message_id is not None
        }
        for message_id in message_ids:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=support_chat_id,
                    message_id=message_id,
                    reply_markup=None,
                )
            except TelegramAPIError:
                logger.exception(
                    "Failed to remove close button from support message %s", message_id
                )
        try:
            await bot.send_message(
                support_chat_id,
                f"✅ Обращение #{ticket.id} закрыто",
                reply_to_message_id=ticket.support_chat_message_id,
            )
        except TelegramAPIError:
            logger.exception("Failed to mark ticket %s closed in support group", ticket.id)
    if user is not None and bot is not None:
        try:
            await bot.send_message(
                user.telegram_id,
                "Поддержка закрыла обращение. Если появится новый вопрос, "
                "открой «Помощь» ещё раз.",
                reply_markup=main_menu_keyboard(),
            )
        except TelegramAPIError:
            logger.exception("Failed to notify user about closed ticket %s", ticket.id)
    try:
        await callback.answer("Обращение закрыто")
    except TelegramAPIError:
        logger.exception("Failed to answer close callback for ticket %s", ticket.id)


@router.message(F.reply_to_message)
async def relay_support_reply(message: Message) -> None:
    settings = get_settings()
    bot = message.bot
    if (
        settings.telegram_support_chat_id is None
        or message.chat.id != settings.telegram_support_chat_id
        or message.reply_to_message is None
        or message.from_user is None
        or message.from_user.is_bot
        or bot is None
    ):
        return
    replied_message_id = message.reply_to_message.message_id
    async with session_factory() as session:
        ticket = await session.scalar(
            select(SupportTicket)
            .outerjoin(SupportMessage, SupportMessage.ticket_id == SupportTicket.id)
            .where(
                (SupportTicket.support_chat_message_id == replied_message_id)
                | (SupportMessage.support_chat_message_id == replied_message_id)
            )
            .limit(1)
        )
        if ticket is None:
            return
        if ticket.status == TicketStatus.CLOSED:
            await message.reply("Обращение уже закрыто. Ответ пользователю не отправлен.")
            return
        user = await session.get(User, ticket.user_id)
        if user is None:
            return
        reply_text = message.text or message.caption or "Сообщение без текста"
        try:
            if message.text:
                await bot.send_message(
                    user.telegram_id,
                    f"Ответ поддержки:\n\n{reply_text}",
                )
            else:
                await bot.send_message(user.telegram_id, "Ответ поддержки:")
                await message.copy_to(user.telegram_id)
        except TelegramAPIError:
            logger.exception("Failed to relay support reply for ticket %s", ticket.id)
            await message.reply("Не удалось отправить ответ пользователю.")
            return
        ticket.status = TicketStatus.IN_PROGRESS
        session.add(
            SupportMessage(
                ticket_id=ticket.id,
                sender_type="support",
                text=reply_text,
                support_chat_message_id=message.message_id,
            )
        )
        await session.commit()
    await message.reply("Ответ отправлен пользователю.")
