"""Content fingerprints for the modelling tables.

Git may check a CSV out with CRLF line endings on Windows and LF on Linux or macOS. A hash of the raw
bytes would then depend on the platform. ``table_sha256`` hashes the file after converting CRLF to LF,
so the same committed table gives the same fingerprint on every checkout. Binary files such as saved
models are hashed byte for byte with ``file_sha256``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


def table_sha256(path: PathLike) -> str:
    """SHA256 of a text table with CRLF line endings normalised to LF."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def file_sha256(path: PathLike) -> str:
    """SHA256 of a file's exact bytes (for binary artifacts)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
