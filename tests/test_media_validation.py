import io

import pytest
from PIL import Image

from zero_semester.media_validation import (
    InvalidMediaError,
    validate_image,
    validate_image_or_video,
    validate_video,
)


def test_real_image_is_detected_from_content() -> None:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), "red").save(output, format="PNG")
    media = validate_image(output.getvalue())
    assert media.media_type == "image/png"
    assert media.suffix == ".png"


def test_html_disguised_as_image_is_rejected() -> None:
    with pytest.raises(InvalidMediaError):
        validate_image(b"<html><script>alert(1)</script></html>")
    with pytest.raises(InvalidMediaError):
        validate_image_or_video(b"<html><script>alert(1)</script></html>")


def test_mp4_header_is_detected_from_content() -> None:
    media = validate_video(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 20)
    assert media.media_type == "video/mp4"
    assert media.suffix == ".mp4"
