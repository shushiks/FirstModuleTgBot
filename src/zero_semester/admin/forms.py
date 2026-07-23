from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from zero_semester.models.enums import AdminRole, PracticeType


class LoginForm(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip()


class AdminCreateForm(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=12, max_length=256)
    role: AdminRole

    @field_validator("username")
    @classmethod
    def normalize_admin_username(cls, value: str) -> str:
        return value.strip()


class ModuleForm(BaseModel):
    school_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    is_required: bool = True

    @field_validator("title", "description")
    @classmethod
    def normalize_module_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class UserSchoolForm(BaseModel):
    school_id: int = Field(gt=0)


class ModuleDetailsForm(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    is_required: bool = True

    @field_validator("title", "description")
    @classmethod
    def normalize_details_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PracticeForm(BaseModel):
    practice_type: PracticeType
    question: str = Field(min_length=1, max_length=4096)
    explanation: str | None = Field(default=None, max_length=4096)
    max_attempts: int = Field(ge=1, le=10)
    options_text: str | None = None
    correct_option: int | None = Field(default=None, ge=1)

    @field_validator("correct_option", mode="before")
    @classmethod
    def empty_correct_option_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("question", "explanation", "options_text")
    @classmethod
    def normalize_practice_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class LmsForm(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    target_url: HttpUrl
    button_text: str = Field(default="Перейти к курсу", min_length=1, max_length=100)
    secret_key: str | None = Field(default=None, max_length=255)
    secret_key_label: str | None = Field(default=None, max_length=120)

    @field_validator("name", "button_text", "secret_key", "secret_key_label")
    @classmethod
    def normalize_lms_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def key_and_label_are_filled_together(self) -> "LmsForm":
        if bool(self.secret_key) != bool(self.secret_key_label):
            raise ValueError("Для нового ключа укажи и фразу, и понятное название")
        return self


class SecretKeyForm(BaseModel):
    lms_course_id: int = Field(gt=0)
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=255)

    @field_validator("label", "value")
    @classmethod
    def normalize_key_text(cls, value: str) -> str:
        return value.strip()


class BroadcastForm(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=4096)
    school_id: int | None = Field(default=None, gt=0)
    scheduled_at: datetime | None = None
    button_text: str | None = Field(default=None, max_length=100)
    button_url: HttpUrl | None = None
    action: str = "send_now"

    @field_validator("title", "text")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("button_text", mode="before")
    @classmethod
    def empty_button_text_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("button_url", "scheduled_at", "school_id", mode="before")
    @classmethod
    def empty_optional_value_is_none(cls, value: object) -> object:
        return None if value == "" else value
