"""PC setup: stdlib only, localhost only, explicit static-file allowlist."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["CAMPERDISPLAY_DATA_DIR"] = str(ROOT.parent / ".camper-private" / "traccar-local")
os.environ["CAMPERDISPLAY_VACATION_DB"] = str(ROOT / "backend" / "data" / "camperdisplay.db")
sys.path.insert(0, str(ROOT / "backend"))
import traccar_client

PORT = 8767
ORIGIN = f"http://127.0.0.1:{PORT}"
FILES = {"/": ("traccar.html", "text/html"), "/js/traccar-settings.js": ("js/traccar-settings.js", "text/javascript")}
FILES.update({"/journey": ("journey-preview.html", "text/html"), "/js/journey-preview.js": ("js/journey-preview.js", "text/javascript"), "/css/journey-preview.css": ("css/journey-preview.css", "text/css")})


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # No URLs, credentials or position data in logs.

    def reply(self, code, body, mime="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' https://unpkg.com; style-src 'self' 'unsafe-inline' https://unpkg.com; img-src 'self' data: https://tile.openstreetmap.org https://unpkg.com; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self):
        self.connection.settimeout(10)
        if self.headers.get("Host") != f"127.0.0.1:{PORT}":
            return self.reply(403, {"detail": "Lokaler Zugriff erforderlich."})
        if self.command == "GET" and self.path in FILES:
            file, mime = FILES[self.path]
            return self.reply(200, (ROOT / "frontend" / file).read_bytes(), mime)
        if self.path not in ("/api/traccar/settings", "/api/traccar/test", "/api/traccar/journey", "/api/traccar/vacations"):
            return self.reply(404, {"detail": "Nicht gefunden."})
        try:
            payload = None
            if self.command != "GET":
                if (self.headers.get("Origin") != ORIGIN
                        or self.headers.get("Content-Type", "").split(";")[0] != "application/json"):
                    return self.reply(403, {"detail": "Nur lokale JSON-Anfragen erlaubt."})
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    return self.reply(413, {"detail": "Ungültige Eingabegröße."})
                payload = json.loads(self.rfile.read(length))
            return self.reply(200, traccar_client.handle(self.command, self.path, payload))
        except traccar_client.TraccarError as exc:
            return self.reply(400, {"detail": str(exc)})
        except (ValueError, UnicodeError):
            return self.reply(400, {"detail": "Ungültige Eingabe."})
        except Exception:
            return self.reply(500, {"detail": "Lokaler Traccar-Dienstfehler."})

    do_GET = dispatch
    do_POST = dispatch
    do_PUT = dispatch


if __name__ == "__main__":
    import traccar_cache
    stop=traccar_cache.start_background_thread()
    print(f"Traccar-Einrichtung bereit: {ORIGIN}", flush=True)
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    finally:
        stop.set()
