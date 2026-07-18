from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from zero_semester.models.base import Base, TimestampMixin
from zero_semester.models.enums import PracticeType, PublicationStatus, SchoolCode


class School(TimestampMixin, Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[SchoolCode] = mapped_column(Enum(SchoolCode, native_enum=False), unique=True)
    name: Mapped[str] = mapped_column(String(150))


class CourseRun(TimestampMixin, Base):
    __tablename__ = "course_runs"
    __table_args__ = (UniqueConstraint("school_id", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"))
    name: Mapped[str] = mapped_column(String(200))
    year: Mapped[int] = mapped_column(Integer)
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, native_enum=False), default=PublicationStatus.DRAFT
    )


class Module(TimestampMixin, Base):
    __tablename__ = "modules"
    __table_args__ = (UniqueConstraint("course_run_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_run_id: Mapped[int] = mapped_column(ForeignKey("course_runs.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    intro_delay_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, native_enum=False), default=PublicationStatus.DRAFT
    )


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    relative_path: Mapped[str] = mapped_column(String(500))
    media_type: Mapped[str] = mapped_column(String(100))
    telegram_file_id: Mapped[str | None] = mapped_column(String(255))
    telegram_fallback_file_id: Mapped[str | None] = mapped_column(String(255))


class Post(TimestampMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("module_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    text: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)


class Card(TimestampMixin, Base):
    __tablename__ = "cards"
    __table_args__ = (UniqueConstraint("post_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    media_asset_id: Mapped[int] = mapped_column(ForeignKey("media_assets.id"))
    caption: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)


class ModuleIntroMedia(Base):
    __tablename__ = "module_intro_media"

    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True
    )
    media_asset_id: Mapped[int] = mapped_column(ForeignKey("media_assets.id"), unique=True)


class Practice(TimestampMixin, Base):
    __tablename__ = "practices"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), unique=True
    )
    practice_type: Mapped[PracticeType] = mapped_column(Enum(PracticeType, native_enum=False))
    question: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    max_attempts: Mapped[int] = mapped_column(Integer, default=2, server_default="2")


class QuizOption(TimestampMixin, Base):
    __tablename__ = "quiz_options"
    __table_args__ = (UniqueConstraint("practice_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    practice_id: Mapped[int] = mapped_column(ForeignKey("practices.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class LmsCourse(TimestampMixin, Base):
    __tablename__ = "lms_courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"))
    name: Mapped[str] = mapped_column(String(200))
    target_url: Mapped[str] = mapped_column(Text)
    short_code: Mapped[str] = mapped_column(String(64), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class ModuleLmsCourse(Base):
    __tablename__ = "module_lms_courses"

    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True
    )
    lms_course_id: Mapped[int] = mapped_column(ForeignKey("lms_courses.id"), primary_key=True)
    button_text: Mapped[str] = mapped_column(String(100), default="Перейти к курсу")


class SecretKey(TimestampMixin, Base):
    __tablename__ = "secret_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    lms_course_id: Mapped[int] = mapped_column(ForeignKey("lms_courses.id"))
    normalized_value: Mapped[str] = mapped_column(String(255), unique=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
