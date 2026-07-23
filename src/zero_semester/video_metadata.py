from __future__ import annotations

import struct
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

_CONTAINER_ATOMS = {b"moov", b"trak"}


def _atom_bounds(file: BinaryIO, start: int, end: int) -> list[tuple[bytes, int, int]]:
    atoms: list[tuple[bytes, int, int]] = []
    position = start
    while position + 8 <= end:
        file.seek(position)
        header = file.read(8)
        if len(header) != 8:
            break
        size, atom_type = struct.unpack(">I4s", header)
        header_size = 8
        if size == 1:
            extended_size = file.read(8)
            if len(extended_size) != 8:
                break
            size = struct.unpack(">Q", extended_size)[0]
            header_size = 16
        elif size == 0:
            size = end - position
        if size < header_size or position + size > end:
            break
        atoms.append((atom_type, position + header_size, position + size))
        position += size
    return atoms


def _track_dimensions(
    file: BinaryIO, payload_start: int, payload_end: int
) -> tuple[int, int] | None:
    file.seek(payload_start)
    version_byte = file.read(1)
    if not version_byte:
        return None
    matrix_offset = 40 if version_byte[0] == 0 else 52
    required_size = matrix_offset + 44
    if payload_end - payload_start < required_size:
        return None
    file.seek(payload_start + matrix_offset)
    raw = file.read(44)
    if len(raw) != 44:
        return None
    matrix = struct.unpack(">9i", raw[:36])
    raw_width, raw_height = struct.unpack(">II", raw[36:])
    width = round(raw_width / 65536)
    height = round(raw_height / 65536)
    if width <= 0 or height <= 0:
        return None
    # A 90/270-degree track matrix means the encoded canvas must be presented rotated.
    if abs(matrix[1]) > abs(matrix[0]) and abs(matrix[3]) > abs(matrix[4]):
        width, height = height, width
    return width, height


@lru_cache(maxsize=256)
def probe_mp4_dimensions(path: Path) -> tuple[int, int] | None:
    """Read display dimensions from MP4/MOV track headers without decoding the video."""
    try:
        file_size = path.stat().st_size
        with path.open("rb") as file:
            for atom_type, atom_start, atom_end in _atom_bounds(file, 0, file_size):
                if atom_type != b"moov":
                    continue
                for child_type, child_start, child_end in _atom_bounds(file, atom_start, atom_end):
                    if child_type not in _CONTAINER_ATOMS:
                        continue
                    for track_type, track_start, track_end in _atom_bounds(
                        file, child_start, child_end
                    ):
                        if track_type == b"tkhd" and (
                            dimensions := _track_dimensions(file, track_start, track_end)
                        ):
                            return dimensions
    except (OSError, struct.error):
        return None
    return None
