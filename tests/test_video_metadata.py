import struct
from pathlib import Path

from zero_semester.video_metadata import probe_mp4_dimensions


def _atom(atom_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", len(payload) + 8, atom_type) + payload


def _video(width: int, height: int, matrix: tuple[int, ...]) -> bytes:
    tkhd = bytearray(84)
    struct.pack_into(">9i", tkhd, 40, *matrix)
    struct.pack_into(">II", tkhd, 76, width * 65536, height * 65536)
    return _atom(b"moov", _atom(b"trak", _atom(b"tkhd", bytes(tkhd))))


def test_probe_mp4_dimensions_reads_portrait_track(tmp_path: Path) -> None:
    path = tmp_path / "portrait.mov"
    identity = (65536, 0, 0, 0, 65536, 0, 0, 0, 1073741824)
    path.write_bytes(_video(464, 848, identity))

    assert probe_mp4_dimensions(path) == (464, 848)


def test_probe_mp4_dimensions_applies_rotation_matrix(tmp_path: Path) -> None:
    path = tmp_path / "rotated.mp4"
    rotate_90 = (0, 65536, 0, -65536, 0, 0, 0, 0, 1073741824)
    path.write_bytes(_video(1920, 1080, rotate_90))

    assert probe_mp4_dimensions(path) == (1080, 1920)
