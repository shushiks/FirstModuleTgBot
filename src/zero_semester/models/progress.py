from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from zero_semester.models.base import Base, TimestampMixin
from zero_semester.models.enums import ProgressStatus


class ModuleProgress(TimestampMixin, Base):
    __tablename__ = "module_progress"
    __table_args__ = (UniqueConstraint("user_id", "module_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"))
    status: Mapped[ProgressStatus] = mapped_column(
        Enum(ProgressStatus, native_enum=False), default=ProgressStatus.NOT_STARTED
    )
    current_post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"))
    current_card_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id"))
    intro_viewed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    practice_started: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]


class PracticeAttempt(TimestampMixin, Base):
    __tablename__ = "practice_attempts"
    __table_args__ = (UniqueConstraint("user_id", "practice_id", "attempt_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    practice_id: Mapped[int] = mapped_column(ForeignKey("practices.id", ondelete="CASCADE"))
    attempt_number: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime | None]


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("practice_attempts.id", ondelete="CASCADE"), primary_key=True
    )
    option_id: Mapped[int] = mapped_column(ForeignKey("quiz_options.id"))
    was_correct: Mapped[bool] = mapped_column(Boolean)


class OpenAnswer(Base):
    __tablename__ = "open_answers"

    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("practice_attempts.id", ondelete="CASCADE"), primary_key=True
    )
    answer_text: Mapped[str] = mapped_column(Text)


class SecretKeyRedemption(TimestampMixin, Base):
    __tablename__ = "secret_key_redemptions"
    __table_args__ = (UniqueConstraint("user_id", "secret_key_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    secret_key_id: Mapped[int] = mapped_column(ForeignKey("secret_keys.id"))


class CourseCompletion(TimestampMixin, Base):
    __tablename__ = "course_completions"
    __table_args__ = (UniqueConstraint("user_id", "course_run_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_run_id: Mapped[int] = mapped_column(ForeignKey("course_runs.id"))
    report_media_asset_id: Mapped[int | None] = mapped_column(ForeignKey("media_assets.id"))
    completed_at: Mapped[datetime]
