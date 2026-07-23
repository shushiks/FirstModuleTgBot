import io
import warnings
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError


class InvalidMediaError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedMedia:
    content: bytes
    suffix: str
    media_type: str


IMAGE_FORMATS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}


def validate_image(content: bytes) -> ValidatedMedia:
    if not content:
        raise InvalidMediaError("Файл пустой")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
                detected = IMAGE_FORMATS.get(image.format or "")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Warning) as error:
        raise InvalidMediaError("Файл не является безопасным изображением") from error
    if detected is None:
        raise InvalidMediaError("Поддерживаются только JPEG, PNG и WebP")
    suffix, media_type = detected
    return ValidatedMedia(content=content, suffix=suffix, media_type=media_type)


def validate_video(content: bytes) -> ValidatedMedia:
    if not content:
        raise InvalidMediaError("Файл пустой")
    if len(content) >= 12 and content[4:8] == b"ftyp":
        major_brand = content[8:12]
        if major_brand == b"qt  ":
            return ValidatedMedia(content, ".mov", "video/quicktime")
        return ValidatedMedia(content, ".mp4", "video/mp4")
    if content.startswith(b"\x1aE\xdf\xa3") and b"webm" in content[:4096].lower():
        return ValidatedMedia(content, ".webm", "video/webm")
    raise InvalidMediaError("Поддерживаются только MP4, MOV и WebM")


def validate_image_or_video(content: bytes) -> ValidatedMedia:
    try:
        return validate_image(content)
    except InvalidMediaError:
        return validate_video(content)
