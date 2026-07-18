from enum import StrEnum


class SchoolCode(StrEnum):
    TECHNOLOGY = "technology"
    DESIGN = "design"


class PublicationStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ProgressStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PracticeType(StrEnum):
    QUIZ = "quiz"
    OPEN_QUESTION = "open_question"


class AdminRole(StrEnum):
    ADMIN = "admin"
    CONTENT_MANAGER = "content_manager"
    SUPPORT = "support"


class TicketStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class BroadcastStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
