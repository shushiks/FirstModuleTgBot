from zero_semester.admin.forms import (
    AdminCreateForm,
    BroadcastForm,
    LmsForm,
    ModuleForm,
    PracticeForm,
    SecretKeyForm,
    UserSchoolForm,
)
from zero_semester.models.enums import AdminRole, PracticeType


def test_module_form_uses_school_instead_of_course_run() -> None:
    form = ModuleForm.model_validate(
        {
            "school_id": "2",
            "title": "  Новый модуль  ",
            "description": "  Описание  ",
            "position": "3",
            "is_required": True,
        }
    )
    assert form.school_id == 2
    assert form.title == "Новый модуль"
    assert form.description == "Описание"


def test_user_school_form_accepts_school_id() -> None:
    form = UserSchoolForm.model_validate({"school_id": "2"})
    assert form.school_id == 2


def test_quiz_form_accepts_configurable_attempts_and_options() -> None:
    form = PracticeForm.model_validate(
        {
            "practice_type": "quiz",
            "question": "Вопрос?",
            "max_attempts": "3",
            "options_text": "Первый\nВторой",
            "correct_option": "2",
        }
    )
    assert form.practice_type == PracticeType.QUIZ
    assert form.max_attempts == 3
    assert form.correct_option == 2


def test_open_question_does_not_require_quiz_option() -> None:
    form = PracticeForm.model_validate(
        {
            "practice_type": "open_question",
            "question": "Что ты понял?",
            "max_attempts": "2",
            "options_text": "",
            "correct_option": "",
        }
    )
    assert form.practice_type == PracticeType.OPEN_QUESTION
    assert form.correct_option is None


def test_poll_is_available_without_correct_answer() -> None:
    form = PracticeForm.model_validate(
        {
            "practice_type": "poll",
            "question": "Какой вариант ближе?",
            "max_attempts": "1",
            "options_text": "Первый\nВторой",
            "correct_option": "",
        }
    )
    assert form.practice_type == PracticeType.POLL
    assert form.correct_option is None


def test_admin_account_form_supports_separate_roles() -> None:
    form = AdminCreateForm.model_validate(
        {"username": " content ", "password": "strong-pass-12", "role": "content_manager"}
    )
    assert form.username == "content"
    assert form.role == AdminRole.CONTENT_MANAGER


def test_lms_form_contains_key_and_real_url() -> None:
    form = LmsForm.model_validate(
        {
            "name": "Курс LMS",
            "target_url": "https://example.com/course",
            "button_text": "Открыть курс",
            "secret_key": "  Ключ 2026  ",
            "secret_key_label": "  Ключ на август  ",
        }
    )
    assert str(form.target_url) == "https://example.com/course"
    assert form.secret_key == "Ключ 2026"
    assert form.secret_key_label == "Ключ на август"


def test_secret_key_form_requires_readable_label() -> None:
    form = SecretKeyForm.model_validate(
        {"lms_course_id": "2", "label": "  Ключ на август  ", "value": "секрет"}
    )
    assert form.label == "Ключ на август"


def test_lms_key_cannot_be_saved_without_label() -> None:
    import pytest

    with pytest.raises(ValueError, match="понятное название"):
        LmsForm.model_validate(
            {
                "name": "Курс LMS",
                "target_url": "https://example.com/course",
                "button_text": "Открыть курс",
                "secret_key": "секрет",
                "secret_key_label": "",
            }
        )


def test_broadcast_form_has_explicit_send_action() -> None:
    form = BroadcastForm.model_validate(
        {"title": "Тест", "text": "Сообщение", "action": "send_now"}
    )
    assert form.action == "send_now"
