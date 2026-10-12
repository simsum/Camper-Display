"""Same-origin photo upload API used by phones in the camper LAN."""
import json
import math
import time

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

import photo_store
import photo_frame_service
import settings_store
import weather_location

router = APIRouter()
NO_STORE = {"Cache-Control": "no-store"}


def _same_origin(request: Request) -> bool:
    return request.headers.get("origin") == str(request.base_url).rstrip("/")


def _upload_metadata(request: Request) -> dict:
    metadata = {}
    try:
        taken_at = float(request.headers.get("x-photo-taken-at", ""))
        if 631152000 <= taken_at <= time.time() + 86400:
            metadata["taken_at"] = taken_at
    except (TypeError, ValueError):
        pass
    try:
        latitude = float(request.headers.get("x-photo-latitude", ""))
        longitude = float(request.headers.get("x-photo-longitude", ""))
        if not (math.isfinite(latitude) and math.isfinite(longitude)
                and -90 <= latitude <= 90 and -180 <= longitude <= 180):
            return metadata
        place = weather_location.resolve(latitude, longitude)
        if place:
            metadata["place"] = place
    except Exception:
        # Missing network or unexpected geocoder data must never block an upload.
        pass
    return metadata


@router.get("/api/photos")
def photos_list() -> JSONResponse:
    photos = photo_store.list_photos()
    return JSONResponse({"photos": photos, "count": len(photos)}, headers=NO_STORE)


@router.get("/api/photos/status")
def photos_status() -> JSONResponse:
    return JSONResponse(photo_frame_service.status(), headers=NO_STORE)


@router.get("/api/photos/file/{photo_id}")
def photos_file(photo_id: str):
    path = photo_store.photo_path(photo_id)
    if path is None:
        return JSONResponse({"detail": "Foto nicht gefunden."}, 404, headers=NO_STORE)
    media_type = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}[path.suffix]
    return FileResponse(path, media_type=media_type, headers={
        "Cache-Control": "private, max-age=86400",
        "X-Content-Type-Options": "nosniff",
    })


@router.post("/api/photos/upload")
async def photos_upload(request: Request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if not _same_origin(request) or content_type not in photo_store.MIME_EXTENSIONS:
        return JSONResponse({"detail": "Nur gleichursprüngliche Bild-Uploads erlaubt."}, 403, headers=NO_STORE)
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > photo_store.MAX_FILE_BYTES:
            return JSONResponse({"detail": "Das Bild ist größer als 8 MB."}, 413, headers=NO_STORE)
    try:
        return JSONResponse(photo_store.add_photo(bytes(data), content_type, _upload_metadata(request)), 201, headers=NO_STORE)
    except ValueError as error:
        return JSONResponse({"detail": str(error)}, 400, headers=NO_STORE)


@router.post("/api/photos/delete")
async def photos_delete(request: Request):
    if not _same_origin(request) or request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
        return JSONResponse({"detail": "Nur gleichursprüngliche JSON-Anfragen erlaubt."}, 403, headers=NO_STORE)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 1024:
            return JSONResponse({"detail": "Eingabe zu groß."}, 413, headers=NO_STORE)
    try:
        photo_id = json.loads(body).get("id")
    except (json.JSONDecodeError, UnicodeError, AttributeError):
        return JSONResponse({"detail": "Ungültige Eingabe."}, 400, headers=NO_STORE)
    if not isinstance(photo_id, str) or not photo_store.delete_photo(photo_id):
        return JSONResponse({"detail": "Foto nicht gefunden."}, 404, headers=NO_STORE)
    return JSONResponse({"ok": True}, headers=NO_STORE)


@router.post("/api/photos/show")
async def photos_show(request: Request):
    if not _same_origin(request) or request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
        return JSONResponse({"detail": "Nur gleichursprüngliche JSON-Anfragen erlaubt."}, 403, headers=NO_STORE)
    if not photo_store.list_photos():
        return JSONResponse({"detail": "Bitte zuerst Fotos hochladen."}, 409, headers=NO_STORE)
    return JSONResponse(photo_frame_service.show(settings_store.load_settings().photo_frame_manual_seconds), headers=NO_STORE)


@router.post("/api/photos/hide")
async def photos_hide(request: Request):
    if not _same_origin(request) or request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
        return JSONResponse({"detail": "Nur gleichursprüngliche JSON-Anfragen erlaubt."}, 403, headers=NO_STORE)
    return JSONResponse(photo_frame_service.hide(), headers=NO_STORE)
