from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaPhoto, MediaUnion, Message

from zero_semester.models import MediaAsset
from zero_semester.storage import LocalMediaStorage
from zero_semester.video_metadata import probe_mp4_dimensions


async def send_media_asset(
    bot: Bot,
    *,
    chat_id: int,
    asset: MediaAsset,
    caption: str | None = None,
) -> Message:
    storage = LocalMediaStorage()
    source = asset.telegram_file_id or FSInputFile(storage.resolve(asset.relative_path))

    if asset.media_type.startswith("image/"):
        return await bot.send_photo(chat_id, source, caption=caption)
    if asset.media_type == "video_note":
        try:
            return await bot.send_video_note(chat_id, source)
        except Exception:
            fallback = asset.telegram_fallback_file_id or FSInputFile(
                storage.resolve(asset.relative_path)
            )
            return await bot.send_video(chat_id, fallback, caption=caption)
    if asset.media_type.startswith("video/"):
        video_path = storage.resolve(asset.relative_path)
        dimensions = probe_mp4_dimensions(video_path)
        return await bot.send_video(
            chat_id,
            source,
            caption=caption,
            width=dimensions[0] if dimensions else None,
            height=dimensions[1] if dimensions else None,
            supports_streaming=True,
        )
    return await bot.send_document(chat_id, source, caption=caption)


async def send_image_album(
    bot: Bot,
    *,
    chat_id: int,
    cards: tuple[tuple[MediaAsset, str | None], ...],
) -> tuple[Message, ...]:
    storage = LocalMediaStorage()
    sent_messages: list[Message] = []
    if len(cards) == 1:
        asset, caption = cards[0]
        sent_messages.append(
            await send_media_asset(bot, chat_id=chat_id, asset=asset, caption=caption)
        )
        return tuple(sent_messages)
    for start in range(0, len(cards), 10):
        chunk = cards[start : start + 10]
        if len(chunk) == 1:
            asset, caption = chunk[0]
            sent_messages.append(
                await send_media_asset(bot, chat_id=chat_id, asset=asset, caption=caption)
            )
            continue
        media: list[MediaUnion] = [
            InputMediaPhoto(
                media=asset.telegram_file_id
                or FSInputFile(storage.resolve(asset.relative_path)),
                caption=caption,
            )
            for asset, caption in chunk
        ]
        sent_messages.extend(await bot.send_media_group(chat_id, media=media))
    return tuple(sent_messages)
