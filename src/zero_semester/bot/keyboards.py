from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from zero_semester.models.enums import ProgressStatus
from zero_semester.services.course import ModuleMenuItem


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
