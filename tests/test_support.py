from zero_semester.bot.keyboards import support_group_close_keyboard
from zero_semester.models.enums import TicketStatus


def test_new_ticket_status_is_explicit() -> None:
    assert TicketStatus.NEW.value == "new"


def test_support_close_button_contains_ticket_id() -> None:
    button = support_group_close_keyboard(42).inline_keyboard[0][0]
    assert button.text == "✅ Закрыть обращение"
    assert button.callback_data == "support:group_close:42"
