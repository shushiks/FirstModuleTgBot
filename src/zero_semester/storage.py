from pathlib import Path
from uuid import uuid4

from zero_semester.config import get_settings


class LocalMediaStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_settings().media_root

    def save(self, content: bytes, suffix: str) -> str:
        safe_suffix = suffix.lower().lstrip(".")
        relative_path = Path(str(uuid4()))
        if safe_suffix:
            relative_path = relative_path.with_suffix(f".{safe_suffix}")
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return str(relative_path)

    def read(self, relative_path: str) -> bytes:
        return (self.root / relative_path).read_bytes()

    def delete(self, relative_path: str) -> None:
        (self.root / relative_path).unlink(missing_ok=True)
