"""Local QR generation for the phone upload page; no external QR service."""
import ipaddress
import os
from urllib.parse import urlsplit, urlunsplit

import qrcode
from qrcode.image.svg import SvgPathFillImage
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter()
NO_STORE = {"Cache-Control": "no-store"}


def upload_url(request: Request) -> str | None:
    """Use an explicit LAN origin, or the non-loopback request origin."""
    base = os.environ.get("CAMPERDISPLAY_PUBLIC_URL", "").strip() or str(request.base_url)
    try:
        parts = urlsplit(base)
        if (len(base) > 512 or any(c.isspace() for c in base)
                or parts.scheme not in ("http", "https") or not parts.hostname
                or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment or parts.path not in ("", "/")
                or "\\" in base):
            return None
        if parts.port is not None and not 1 <= parts.port <= 65535:
            return None
        host = parts.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith(".localhost"):
            return None
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            pass  # A LAN DNS name such as camperdisplay.local is also supported.
        else:
            if address.is_loopback or address.is_unspecified:
                return None
        return urlunsplit((parts.scheme, parts.netloc, "/photos", "", ""))
    except ValueError:
        return None


@router.get("/api/photos/share")
def share(request: Request) -> JSONResponse:
    return JSONResponse({"url": upload_url(request)}, headers=NO_STORE)


@router.get("/api/photos/qr.svg", include_in_schema=False)
def share_qr(request: Request) -> Response:
    url = upload_url(request)
    if not url:
        raise HTTPException(503, "Für den Kiosk zuerst die LAN-Adresse konfigurieren.")
    qr = qrcode.make(url, image_factory=SvgPathFillImage, border=4)
    return Response(qr.to_string(), media_type="image/svg+xml", headers=NO_STORE)
