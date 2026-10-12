"""Read-only Traccar connection setup. Secrets never enter public Settings."""
import json
import math
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

DB_PATH = Path(os.environ.get("CAMPERDISPLAY_DATA_DIR", Path(__file__).parent / "data")) / "traccar-private.db"
DEFAULT_URL = ""
LOCK = threading.RLock()
TEST_LOCK = threading.Lock()


class TraccarError(Exception):
    pass


class TraccarTooLarge(TraccarError):
    pass


def normalize_url(value):
    try:
        if not isinstance(value, str) or len(value) > 2048 or any(c.isspace() for c in value):
            raise ValueError()
        parts = urlsplit(value)
        if (parts.scheme not in ("http", "https") or not parts.hostname
                or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment or "\\" in value):
            raise ValueError()
        if parts.port is not None and not 1 <= parts.port <= 65535:
            raise ValueError()
        path = parts.path.rstrip("/")
        if "%" in path or any(p in (".", "..") for p in path.split("/")):
            raise ValueError()
        if not path.endswith("/api"):
            path += "/api"
        return urlunsplit((parts.scheme, parts.netloc.lower(), path, "", ""))
    except (ValueError, TypeError):
        raise TraccarError("Bitte eine HTTP-/HTTPS-API-Adresse ohne Zugangsdaten, Parameter oder Fragment eingeben.") from None


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=5)
    if os.name != "nt":
        DB_PATH.chmod(0o600)
    db.execute("PRAGMA synchronous=FULL")
    db.execute("CREATE TABLE IF NOT EXISTS connection (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)")
    db.commit()
    return db


def load_private():
    with LOCK:
        db = connect()
        try:
            row = db.execute("SELECT data FROM connection WHERE id=1").fetchone()
            return json.loads(row[0]) if row else {"api_url": DEFAULT_URL, "token": "", "device_id": None}
        finally:
            db.close()


def public_config(config=None):
    config = config if config is not None else load_private()
    return {"api_url": config["api_url"], "device_id": config["device_id"], "token_saved": bool(config["token"])}


def candidate(payload, stored):
    if not isinstance(payload, dict):
        raise TraccarError("Ungültige Eingabe.")
    url = normalize_url(payload.get("api_url", stored["api_url"]))
    token = payload.get("token", "")
    if not isinstance(token, str) or len(token) > 8192 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise TraccarError("Der Token enthält ungültige Zeichen.")
    # A saved credential is bound to its exact server + API path.
    if not token and url == stored["api_url"]:
        token = stored["token"]
    if payload.get("clear_token") is True:
        token = ""
    device = payload.get("device_id")
    if device is not None and (type(device) is not int or device <= 0):
        raise TraccarError("Bitte ein gültiges Fahrzeug auswählen.")
    return {"api_url": url, "token": token, "device_id": device}


def save(payload):
    with LOCK:
        result = candidate(payload, load_private())
        db = connect()
        try:
            with db:
                db.execute("INSERT INTO connection VALUES(1, ?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (json.dumps(result),))
        finally:
            db.close()
        return public_config(result)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_json(config, endpoint, max_bytes=2_000_000, timeout=6):
    # No ambient proxy, cookie persistence, query-string token or redirects.
    opener = build_opener(ProxyHandler({}), NoRedirect())
    req = Request(config["api_url"] + endpoint, headers={
        "Authorization": "Bearer " + config["token"], "Accept": "application/json",
        "User-Agent": "CamperDisplay/0.6 Traccar-readonly",
    })
    try:
        with opener.open(req, timeout=timeout) as response:
            if "application/json" not in response.headers.get("Content-Type", "").lower():
                raise TraccarError("Keine JSON-API-Antwort. Bitte die API-Adresse prüfen.")
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise TraccarTooLarge("Antwort zu groß. Bitte den Zeitraum verkleinern.")
            return json.loads(data)
    except HTTPError as exc:
        code = exc.code
        exc.close()
        if code in (401, 403):
            raise TraccarError("Zugriff abgelehnt. Token, Ablaufdatum und Benutzerrechte prüfen.") from None
        if 300 <= code < 400:
            raise TraccarError("Weiterleitung abgelehnt. Bitte die endgültige API-Adresse eintragen.") from None
        raise TraccarError(f"Traccar antwortet mit HTTP {code}.") from None
    except (URLError, TimeoutError, OSError):
        raise TraccarError("Server nicht erreichbar oder TLS-Prüfung fehlgeschlagen. Adresse, Netzwerk/VPN und Zertifikat prüfen.") from None
    except (ValueError, UnicodeError):
        raise TraccarError("Die API-Antwort konnte nicht gelesen werden.") from None


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def test_connection(payload):
    if not TEST_LOCK.acquire(blocking=False):
        raise TraccarError("Ein Verbindungstest läuft bereits.")
    try:
        config = candidate(payload, load_private())
        if not config["token"]:
            raise TraccarError("Bitte zuerst einen Token eingeben.")
        # /session is a browser-cookie endpoint: it returns 404 without a cookie,
        # even with valid Bearer authorization. Authenticate directly on /devices.
        # Do not put the token in a session URL or decode/trust token claims.
        # Account role is configured in Traccar, not verified by this probe.
        devices = fetch_json(config, "/devices")
        if not isinstance(devices, list):
            raise TraccarError("Unerwartete Fahrzeugantwort.")
        devices = [{"id": d["id"], "name": str(d.get("name", "Fahrzeug"))[:120]}
                   for d in devices if isinstance(d, dict) and type(d.get("id")) is int and d["id"] > 0]
        selected = config["device_id"]
        if selected is not None and not any(d["id"] == selected for d in devices):
            raise TraccarError("Das ausgewählte Fahrzeug ist für diesen Zugang nicht freigegeben.")
        if selected is None and len(devices) == 1:
            selected = devices[0]["id"]
        result = {"ok": True, "devices": devices, "device_id": selected, "position": None,
                  "permissions_verified": False,
                  "message": "Verbindung erfolgreich. Fahrzeug auswählen und speichern." if devices else "Verbindung erfolgreich, aber kein Fahrzeug freigegeben."}
        if selected is not None:
            positions = fetch_json(config, f"/positions?deviceId={selected}")
            if not isinstance(positions, list):
                raise TraccarError("Unerwartete Positionsantwort.")
            rows = [p for p in positions if isinstance(p, dict) and p.get("deviceId") == selected]
            if rows:
                p = max(rows, key=lambda p: str(p.get("fixTime", "")))
                try:
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(p["fixTime"].replace("Z", "+00:00"))).total_seconds()
                    if not math.isfinite(age):
                        age = None
                except (KeyError, ValueError, TypeError):
                    age = None
                speed = number(p.get("speed"))
                result["position"] = {"fix_time": str(p.get("fixTime", ""))[:40], "age_seconds": age,
                    "stale": age is None or age > 120 or age < -60 or p.get("valid") is not True,
                    "speed_kmh": round(speed * 1.852, 1) if speed is not None else None,
                    "altitude_m": number(p.get("altitude"))}
        return result
    finally:
        TEST_LOCK.release()


def handle(method, path, payload=None):
    if method == "POST" and path == "/api/traccar/journey":
        from traccar_cache import service
        return service.request(payload)
    if method == "GET" and path == "/api/traccar/vacations":
        from traccar_journey import vacations
        return {"vacations": vacations()}
    if method == "GET" and path == "/api/traccar/settings":
        return public_config()
    if method == "PUT" and path == "/api/traccar/settings":
        return save(payload)
    if method == "POST" and path == "/api/traccar/test":
        return test_connection(payload)
    raise TraccarError("Unbekannter Traccar-Aufruf.")
