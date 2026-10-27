from zero_semester.models.enums import BroadcastStatus


def test_broadcast_has_draft_and_scheduled_states() -> None:
    assert BroadcastStatus.DRAFT.value == "draft"
    assert BroadcastStatus.SCHEDULED.value == "scheduled"
