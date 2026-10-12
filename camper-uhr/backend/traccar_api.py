"""Production API adapter; same service as the loopback-only PC setup server."""
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import traccar_client

router = APIRouter()


@router.api_route("/api/traccar/{action}", methods=["GET", "PUT", "POST"])
async def traccar_endpoint(action: str, request: Request):
    from starlette.concurrency import run_in_threadpool
    headers = {"Cache-Control": "no-store"}
    if request.method != "GET":
        if (request.headers.get("origin") != str(request.base_url).rstrip("/")
                or request.headers.get("content-type", "").split(";")[0] != "application/json"):
            return JSONResponse({"detail": "Nur gleichursprüngliche JSON-Anfragen erlaubt."}, 403, headers=headers)
    try:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 16384:
                return JSONResponse({"detail": "Eingabe zu groß."}, 413, headers=headers)
        payload = json.loads(body) if body else None
        result = await run_in_threadpool(traccar_client.handle, request.method, f"/api/traccar/{action}", payload)
        return JSONResponse(result, headers=headers)
    except (json.JSONDecodeError, UnicodeError):
        return JSONResponse({"detail": "Ungültige Eingabe."}, 400, headers=headers)
    except traccar_client.TraccarError as exc:
        return JSONResponse({"detail": str(exc)}, 400, headers=headers)
    except Exception:
        return JSONResponse({"detail": "Lokaler Traccar-Dienstfehler."}, 500, headers=headers)
