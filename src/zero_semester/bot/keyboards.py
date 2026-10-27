from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from zero_semester.models.enums import ProgressStatus
from zero_semester.services.course import ModuleMenuItem
from zero_semester.services.practice import PracticeView


def school_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Школа технологий", callback_data="school:technology")],
            [InlineKeyboardButton(text="Школа дизайна", callback_data="school:design")],
        ]
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Модули", callback_data="menu:modules")],
            [InlineKeyboardButton(text="🔑 Секретный ключ", callback_data="menu:secret")],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="menu:support")],
        ]
    )


def support_group_close_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Закрыть обращение",
                    callback_data=f"support:group_close:{ticket_id}",
                )
            ]
        ]
    )


def modules_keyboard(items: list[ModuleMenuItem]) -> InlineKeyboardMarkup:
    icons = {
        ProgressStatus.NOT_STARTED: "▫️",
        ProgressStatus.IN_PROGRESS: "⏸",
        ProgressStatus.COMPLETED: "✅",
    }
    rows = [
        [
            InlineKeyboardButton(
                text=f"{icons[item.status]} {item.position}. {item.title}",
                callback_data=f"module:{item.module_id}",
            )
        ]
        for item in items
    ]
    rows.append([InlineKeyboardButton(text="← В меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def practice_keyboard(practice: PracticeView) -> InlineKeyboardMarkup:
    callback_prefix = "poll" if practice.practice_type.value == "poll" else "quiz"
    rows = [
        [
            InlineKeyboardButton(
                text=option.text,
                callback_data=f"{callback_prefix}:{practice.id}:{option.id}",
            )
        ]
        for option in practice.options
    ]
    rows.append([InlineKeyboardButton(text="← В меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
