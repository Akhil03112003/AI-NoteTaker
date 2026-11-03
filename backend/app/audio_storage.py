"""Private, bounded, generated-name storage for uploaded audio."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import UUID


CHUNK_SIZE = 1024 * 1024
MIME_BY_EXTENSION = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
}
ACCEPTED_MIME_TYPES = {
    ".mp3": {"audio/mpeg", "audio/mp3", "audio/x-mp3", "application/octet-stream"},
    ".wav": {"audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave", "application/octet-stream"},
    ".m4a": {"audio/mp4", "audio/m4a", "video/mp4", "application/mp4", "application/octet-stream"},
    ".webm": {"audio/webm", "video/webm", "application/octet-stream"},
}


class AudioRejected(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class StorageUnavailable(Exception):
    pass


@dataclass(frozen=True)
class StoredAudio:
    storage_key: str
    original_filename: str
    media_type: str
    file_size_bytes: int
    path: Path


def sanitize_filename(filename: str | None) -> str:
    if not filename:
        return ""
    basename = filename.replace("\\", "/").split("/")[-1]
    safe = "".join(char for char in basename if ord(char) >= 32 and ord(char) != 127)
    safe = safe.strip().strip(".")
    return safe[:255]


def _signature_matches(extension: str, header: bytes) -> bool:
    if extension == ".wav":
        return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"
    if extension == ".m4a":
        return len(header) >= 12 and header[4:8] == b"ftyp"
    if extension == ".webm":
        return header.startswith(b"\x1a\x45\xdf\xa3")
    if extension == ".mp3":
        return header.startswith(b"ID3") or (
            len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
        )
    return False


def _inside_root(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise StorageUnavailable("storage path escaped configured root") from exc
    return resolved


def store_audio(
    source: BinaryIO,
    *,
    filename: str | None,
    content_type: str | None,
    storage_root: Path,
    session_id: UUID,
    max_bytes: int,
) -> StoredAudio:
    safe_filename = sanitize_filename(filename)
    extension = Path(safe_filename).suffix.lower()
    if extension not in MIME_BY_EXTENSION:
        raise AudioRejected("unsupported_audio_type", "Choose an MP3, WAV, M4A, or WebM audio file.", 415)

    declared_type = (content_type or "").split(";", 1)[0].strip().lower()
    if declared_type and declared_type not in ACCEPTED_MIME_TYPES[extension]:
        raise AudioRejected("unsupported_audio_type", "The file type and media type do not match.", 415)
    if max_bytes <= 0:
        raise StorageUnavailable("upload limit configuration is invalid")

    root: Path | None = None
    final_path: Path | None = None
    temporary_path: Path | None = None
    try:
        root = storage_root.resolve()
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        storage_key = f"{session_id.hex}{extension}"
        final_path = _inside_root(root, root / storage_key)
        temporary_path = _inside_root(root, root / f"{storage_key}.part")
        if final_path.exists() or temporary_path.exists():
            raise StorageUnavailable("generated storage name already exists")

        total = 0
        header = bytearray()
        with temporary_path.open("xb") as target:
            while True:
                chunk = source.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise AudioRejected("upload_too_large", "The audio file exceeds the configured size limit.", 413)
                if len(header) < 16:
                    header.extend(chunk[: 16 - len(header)])
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())

        if total == 0:
            raise AudioRejected("empty_audio", "The uploaded audio file is empty.", 400)
        if not _signature_matches(extension, bytes(header)):
            raise AudioRejected("invalid_audio_signature", "The file contents do not match the selected audio type.", 415)

        os.replace(temporary_path, final_path)
        return StoredAudio(
            storage_key=storage_key,
            original_filename=safe_filename,
            media_type=MIME_BY_EXTENSION[extension],
            file_size_bytes=total,
            path=final_path,
        )
    except AudioRejected:
        _remove_if_present(temporary_path)
        _remove_if_present(final_path)
        raise
    except OSError as exc:
        _remove_if_present(temporary_path)
        _remove_if_present(final_path)
        raise StorageUnavailable("local audio storage failed") from exc
    except StorageUnavailable:
        _remove_if_present(temporary_path)
        _remove_if_present(final_path)
        raise
    except Exception as exc:
        _remove_if_present(temporary_path)
        _remove_if_present(final_path)
        raise StorageUnavailable("local audio storage failed") from exc


def delete_stored_audio(storage_root: Path, storage_key: str) -> bool:
    # Storage keys are generated by this module. Reject separators defensively.
    if not re.fullmatch(r"[0-9a-f]{32}\.(mp3|wav|m4a|webm)", storage_key):
        return False
    try:
        root = storage_root.resolve()
        candidate = _inside_root(root, root / storage_key)
        candidate.unlink(missing_ok=True)
        _remove_if_present(candidate.with_suffix(candidate.suffix + ".part"))
        return True
    except (OSError, StorageUnavailable):
        return False


def _remove_if_present(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
