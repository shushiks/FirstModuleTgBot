from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zero_semester.models.base import Base, TimestampMixin
from zero_semester.models.enums import BroadcastStatus, DeliveryStatus, TicketStatus


class SupportTicket(TimestampMixin, Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(100))
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False), default=TicketStatus.NEW
    )
    support_chat_message_id: Mapped[int | None] = mapped_column(BigInteger)
    closed_at: Mapped[datetime | None]


class SupportMessage(TimestampMixin, Base):
    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id", ondelete="CASCADE"))
    sender_type: Mapped[str] = mapped_column(String(20))
    text: Mapped[str | None] = mapped_column(Text)
    support_chat_message_id: Mapped[int | None] = mapped_column(BigInteger)


class Broadcast(TimestampMixin, Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    button_text: Mapped[str | None] = mapped_column(String(100))
    button_url: Mapped[str | None] = mapped_column(Text)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"))
    scheduled_at: Mapped[datetime | None]
    status: Mapped[BroadcastStatus] = mapped_column(
        Enum(BroadcastStatus, native_enum=False), default=BroadcastStatus.DRAFT
    )


class BroadcastRecipient(TimestampMixin, Base):
    __tablename__ = "broadcast_recipients"
    __table_args__ = (UniqueConstraint("broadcast_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(ForeignKey("broadcasts.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, native_enum=False), default=DeliveryStatus.PENDING
    )
    sent_at: Mapped[datetime | None]
    error: Mapped[str | None] = mapped_column(Text)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"))
    course_run_id: Mapped[int | None] = mapped_column(ForeignKey("course_runs.id"))
    module_id: Mapped[int | None] = mapped_column(ForeignKey("modules.id"))
    event_name: Mapped[str] = mapped_column(String(100), index=True)
    properties: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
