"""Small, local-only photo library for the digital frame module."""
from __future__ import annotations

import os
import json
import re
import threading
import time
from pathlib import Path
from uuid import uuid4

import settings_store

PHOTO_DIR = settings_store.DATA_DIR / "photos"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_LIBRARY_BYTES = 2 * 1024 * 1024 * 1024
MAX_PHOTOS = 500
PHOTO_ID = re.compile(r"^[a-f0-9]{32}\.(?:jpg|png|webp)$")
MIME_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_lock = threading.Lock()
DIMENSION_SCAN_BYTES = 1024 * 1024


def _valid_signature(data: bytes, extension: str) -> bool:
    if extension == "jpg":
        return data.startswith(b"\xff\xd8\xff")
    if extension == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"


def _image_dimensions(data: bytes) -> tuple[int, int] | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return (width, height) if width and height else None
    if data.startswith(b"\xff\xd8\xff"):
        offset = 2
        start_of_frame = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
        while offset + 8 < len(data):
            if data[offset] != 0xFF:
                offset += 1
                continue
            while offset < len(data) and data[offset] == 0xFF:
                offset += 1
            if offset >= len(data):
                break
            marker = data[offset]
            offset += 1
            if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
                continue
            if offset + 2 > len(data):
                break
            segment_length = int.from_bytes(data[offset:offset + 2], "big")
            if segment_length < 2 or offset + segment_length > len(data):
                break
            if marker in start_of_frame and segment_length >= 7:
                height = int.from_bytes(data[offset + 3:offset + 5], "big")
                width = int.from_bytes(data[offset + 5:offset + 7], "big")
                return (width, height) if width and height else None
            offset += segment_length
        return None
    if len(data) >= 30 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X":
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            return width, height
        if chunk == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
            width = int.from_bytes(data[26:28], "little") & 0x3FFF
            height = int.from_bytes(data[28:30], "little") & 0x3FFF
            return (width, height) if width and height else None
        if chunk == b"VP8L" and data[20] == 0x2F:
            b1, b2, b3, b4 = data[21:25]
            width = 1 + (((b2 & 0x3F) << 8) | b1)
            height = 1 + (((b4 & 0x0F) << 10) | (b3 << 2) | ((b2 & 0xC0) >> 6))
            return width, height
    return None


def _dimension_fields(data: bytes) -> dict:
    dimensions = _image_dimensions(data)
    if dimensions is None:
        return {}
    width, height = dimensions
    return {"width": width, "height": height, "aspect_ratio": round(width / height, 5)}


def _file_dimension_fields(path: Path) -> dict:
    try:
        with path.open("rb") as handle:
            return _dimension_fields(handle.read(DIMENSION_SCAN_BYTES))
    except OSError:
        return {}


def _files() -> list[Path]:
    if not PHOTO_DIR.exists():
        return []
    return [path for path in PHOTO_DIR.iterdir() if path.is_file() and PHOTO_ID.fullmatch(path.name)]


def _metadata_path(photo_id: str) -> Path:
    return PHOTO_DIR / f"{photo_id}.json"


def _read_metadata(photo_id: str) -> dict:
    path = _metadata_path(photo_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    result = {}
    taken_at = data.get("taken_at")
    if isinstance(taken_at, (int, float)) and 631152000 <= taken_at <= time.time() + 86400:
        result["taken_at"] = round(taken_at)
    place = data.get("place")
    if isinstance(place, str) and place.strip():
        result["place"] = place.strip()[:160]
    return result


def list_photos() -> list[dict]:
    with _lock:
        files = sorted(_files(), key=lambda path: path.stat().st_mtime, reverse=True)
        return [
            {
                "id": path.name,
                "url": f"/api/photos/file/{path.name}",
                "added_at": round(path.stat().st_mtime),
                "size_bytes": path.stat().st_size,
                **_file_dimension_fields(path),
                **_read_metadata(path.name),
            }
            for path in files
        ]


def add_photo(data: bytes, content_type: str, metadata: dict | None = None) -> dict:
    extension = MIME_EXTENSIONS.get(content_type)
    if extension is None:
        raise ValueError("Bitte JPEG, PNG oder WebP verwenden.")
    if not data or len(data) > MAX_FILE_BYTES:
        raise ValueError("Das Bild ist leer oder größer als 8 MB.")
    if not _valid_signature(data, extension):
        raise ValueError("Die Bilddatei ist beschädigt oder hat ein falsches Format.")
    with _lock:
        PHOTO_DIR.mkdir(parents=True, exist_ok=True)
        files = _files()
        if len(files) >= MAX_PHOTOS:
            raise ValueError("Es sind bereits 500 Fotos gespeichert.")
        if sum(path.stat().st_size for path in files) + len(data) > MAX_LIBRARY_BYTES:
            raise ValueError("Der reservierte Fotospeicher von 2 GB ist voll.")
        photo_id = f"{uuid4().hex}.{extension}"
        temporary = PHOTO_DIR / (photo_id + ".tmp")
        destination = PHOTO_DIR / photo_id
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        os.chmod(destination, 0o600)
        now = time.time()
        os.utime(destination, (now, now))
        result = {
            "id": photo_id,
            "url": f"/api/photos/file/{photo_id}",
            "added_at": round(now),
            "size_bytes": len(data),
            **_dimension_fields(data),
        }
        clean_metadata = {}
        metadata = metadata or {}
        taken_at = metadata.get("taken_at")
        if isinstance(taken_at, (int, float)) and 631152000 <= taken_at <= now + 86400:
            clean_metadata["taken_at"] = round(taken_at)
        place = metadata.get("place")
        if isinstance(place, str) and place.strip():
            clean_metadata["place"] = place.strip()[:160]
        if clean_metadata:
            sidecar = _metadata_path(photo_id)
            temporary_sidecar = sidecar.with_suffix(sidecar.suffix + ".tmp")
            temporary_sidecar.write_text(json.dumps(clean_metadata, ensure_ascii=False), encoding="utf-8")
            os.chmod(temporary_sidecar, 0o600)
            os.replace(temporary_sidecar, sidecar)
            result.update(clean_metadata)
        return result


def photo_path(photo_id: str) -> Path | None:
    if not PHOTO_ID.fullmatch(photo_id):
        return None
    path = PHOTO_DIR / photo_id
    return path if path.is_file() else None


def delete_photo(photo_id: str) -> bool:
    with _lock:
        path = photo_path(photo_id)
        if path is None:
            return False
        path.unlink()
        _metadata_path(photo_id).unlink(missing_ok=True)
        return True
