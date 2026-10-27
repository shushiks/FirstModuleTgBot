from zero_semester.bot.handlers.modules import _can_use_tracking_redirect, _lms_button_url
from zero_semester.bot.keyboards import modules_keyboard
from zero_semester.models.enums import ProgressStatus
from zero_semester.services.course import ModuleContentView, ModuleMenuItem


def test_module_menu_contains_progress_and_callback() -> None:
    keyboard = modules_keyboard(
        [
            ModuleMenuItem(
                module_id=42,
                title="Вуз vs школа",
                position=1,
                status=ProgressStatus.IN_PROGRESS,
            )
        ]
    )
    button = keyboard.inline_keyboard[0][0]
    assert button.callback_data == "module:42"
    assert "⏸" in button.text


def test_localhost_cannot_be_used_for_telegram_redirect() -> None:
    assert not _can_use_tracking_redirect("http://localhost:8000")
    assert not _can_use_tracking_redirect("http://127.0.0.1:8000")
    assert _can_use_tracking_redirect("https://bot.example.com")


def test_lms_button_falls_back_to_real_url_in_local_environment() -> None:
    content = ModuleContentView(
        module_id=42,
        title="Модуль",
        description=None,
        intro_asset=None,
        cards=(),
        practice_id=7,
        practice_type=None,
        lms_short_code="course",
        lms_button_text="Перейти к курсу",
        lms_target_url="https://lms.example.com/course",
    )
    assert _lms_button_url(content, user_id=1) == "https://lms.example.com/course"
