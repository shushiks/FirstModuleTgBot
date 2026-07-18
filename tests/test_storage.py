from pathlib import Path

from zero_semester.storage import LocalMediaStorage


def test_local_media_storage_round_trip(tmp_path: Path) -> None:
    storage = LocalMediaStorage(tmp_path)
    relative_path = storage.save(b"video", "mp4")
    assert storage.read(relative_path) == b"video"
    storage.delete(relative_path)
    assert not (tmp_path / relative_path).exists()
