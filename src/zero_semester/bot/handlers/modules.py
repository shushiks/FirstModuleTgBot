from ipaddress import ip_address
from urllib.parse import urlsplit

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from zero_semester.bot.senders import send_image_album, send_media_asset
from zero_semester.config import get_settings
from zero_semester.database import session_factory
from zero_semester.models import MediaAsset
from zero_semester.repositories.events import EventRepository
from zero_semester.repositories.progress import ProgressRepository
from zero_semester.repositories.users import UserRepository
from zero_semester.security import sign_payload
from zero_semester.services.course import ModuleContentView, get_module_content

router = Router(name="modules")


def _telegram_file_id(message: Message) -> str | None:
    if message.photo:
        return message.photo[-1].file_id
    if message.video:
        return message.video.file_id
    if message.document:
        return message.document.file_id
    if message.video_note:
        return message.video_note.file_id
    return None


async def _cache_delivery_file_ids(pairs: list[tuple[int, Message]]) -> None:
    updates = [
        (asset_id, file_id)
        for asset_id, message in pairs
        if (file_id := _telegram_file_id(message)) is not None
    ]
    if not updates:
        return
    async with session_factory() as session:
        for asset_id, file_id in updates:
            asset = await session.get(MediaAsset, asset_id)
            if asset is not None and asset.telegram_file_id != file_id:
                asset.telegram_file_id = file_id
        await session.commit()


def _can_use_tracking_redirect(base_url: str) -> bool:
    parsed = urlsplit(base_url)
    hostname = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not hostname:
        return False
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        return False
    try:
        return ip_address(hostname).is_global
    except ValueError:
        return True


def _lms_button_url(content: ModuleContentView, *, user_id: int) -> str | None:
    public_base_url = get_settings().public_base_url.rstrip("/")
    if content.lms_short_code and _can_use_tracking_redirect(public_base_url):
        token = sign_payload(
            {
                "user_id": user_id,
                "module_id": content.module_id,
                "short_code": content.lms_short_code,
            },
            purpose="lms_click",
            ttl_seconds=180 * 24 * 60 * 60,
        )
        return f"{public_base_url}/go/{content.lms_short_code}?t={token}"
    return content.lms_target_url


def _module_actions(content: ModuleContentView, *, user_id: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    lms_url = _lms_button_url(content, user_id=user_id)
    if lms_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text=content.lms_button_text or "Перейти к курсу",
                    url=lms_url,
                )
            ]
        )
    if content.practice_id is not None:
        practice_labels = {
            "quiz": "Пройти квиз",
            "open_question": "Ответить на вопрос",
            "poll": "Пройти опрос",
        }
        rows.append(
            [
                InlineKeyboardButton(
                    text=practice_labels.get(
                        content.practice_type.value if content.practice_type else "",
                        "Перейти к практике",
                    ),
                    callback_data=f"practice:{content.practice_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="← В меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("module:"))
async def open_module(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return
    module_id = int(callback.data.split(":", 1)[1])
    async with session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        content = (
            await get_module_content(session, module_id=module_id, school_id=user.school_id)
            if user is not None
            else None
        )
        if content is not None and user is not None:
            await ProgressRepository(session).mark_module_started(user.id, module_id)
            await EventRepository(session).add(
                "module_opened",
                user_id=user.id,
                school_id=user.school_id,
                module_id=module_id,
            )
            await session.commit()
    if user is None:
        await callback.answer("Сначала выполни /start", show_alert=True)
        return
    if content is None:
        await callback.answer("Модуль не опубликован", show_alert=True)
        return
    title = f"{content.title}\n\n{content.description or ''}".strip()
    try:
        await callback.message.edit_text(title, reply_markup=None)
    except TelegramBadRequest:
        await callback.message.answer(title)
    bot = callback.bot
    delivery_pairs: list[tuple[int, Message]] = []
    if bot is not None and content.intro_asset is not None:
        sent_intro = await send_media_asset(
            bot,
            chat_id=callback.message.chat.id,
            asset=content.intro_asset,
        )
        delivery_pairs.append((content.intro_asset.id, sent_intro))
    if bot is not None and content.cards:
        sent_cards = await send_image_album(
            bot,
            chat_id=callback.message.chat.id,
            cards=tuple((card.asset, card.caption) for card in content.cards),
        )
        delivery_pairs.extend(
            (card.asset.id, sent_message)
            for card, sent_message in zip(content.cards, sent_cards, strict=True)
        )
    await _cache_delivery_file_ids(delivery_pairs)
    await callback.message.answer(
        "Материалы модуля открыты.",
        reply_markup=_module_actions(content, user_id=user.id),
    )
    await callback.answer()
