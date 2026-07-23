from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import SupportMessage, SupportTicket
from zero_semester.repositories.events import EventRepository


async def create_support_ticket(
    session: AsyncSession,
    *,
    user_id: int,
    category: str,
    text: str | None,
    support_chat_message_id: int,
) -> SupportTicket:
    ticket = SupportTicket(
        user_id=user_id,
        category=category,
        support_chat_message_id=support_chat_message_id,
    )
    session.add(ticket)
    await session.flush()
    session.add(
        SupportMessage(
            ticket_id=ticket.id,
            sender_type="user",
            text=text,
            support_chat_message_id=support_chat_message_id,
        )
    )
    await EventRepository(session).add(
        "support_created", user_id=user_id, properties={"ticket_id": ticket.id}
    )
    await session.commit()
    return ticket


async def add_support_message(
    session: AsyncSession,
    *,
    ticket: SupportTicket,
    text: str | None,
    support_chat_message_id: int,
) -> None:
    session.add(
        SupportMessage(
            ticket_id=ticket.id,
            sender_type="user",
            text=text,
            support_chat_message_id=support_chat_message_id,
        )
    )
    await session.commit()
