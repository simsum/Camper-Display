import json
from copy import deepcopy
import os
import sqlite3
from pathlib import Path

from models import ScreenConfig, Settings

DATA_DIR = Path(os.environ.get("CAMPERDISPLAY_DATA_DIR", Path(__file__).parent / "data"))
DB_PATH = DATA_DIR / "camperdisplay.db"

DEFAULTS = Settings()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA wal_autocheckpoint=100")
    conn.execute("PRAGMA journal_size_limit=1048576")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS trip (id INTEGER PRIMARY KEY CHECK (id = 1), "
        "total_km REAL NOT NULL DEFAULT 0, last_lat REAL, last_lon REAL)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO trip (id, total_km, last_lat, last_lon) VALUES (1, 0, NULL, NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS trip_route (id INTEGER PRIMARY KEY CHECK (id = 1), "
        "start_lat REAL, start_lon REAL, dest_name TEXT, dest_lat REAL, dest_lon REAL)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO trip_route (id, start_lat, start_lon, dest_name, dest_lat, dest_lon) "
        "VALUES (1, NULL, NULL, NULL, NULL, NULL)"
    )
    return conn


def healthcheck() -> bool:
    """Cheap readiness check used by systemd/kiosk startup."""
    try:
        conn = _connect()
        try:
            row = conn.execute("PRAGMA quick_check").fetchone()
            return bool(row and row[0] == "ok")
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def _migrate(data: dict) -> dict:
    data = deepcopy(data)  # Keep the stored snapshot intact for the persistence comparison.
    legacy_schema = data.get("config_version", 1) < 2
    default_by_id = {screen.id: screen for screen in DEFAULTS.screens}
    raw_screens = data.get("screens") or []
    # An explicit new-style module wins if an old client also submits 'clock'.
    explicit_ids = {raw if isinstance(raw, str) else raw.get("id") for raw in raw_screens}
    migrated_screens = []
    known_ids = set()

    for raw in raw_screens:
        raw = {"id": raw, "enabled": True} if isinstance(raw, str) else dict(raw)
        screen_id = raw.get("id")
        if screen_id in {"trip", "news", "photo_frame"}:
            continue
        was_legacy_clock = screen_id == "clock"
        if screen_id == "clock":
            theme = data.get("theme", "flip")
            screen_id = "clock_" + (theme if theme in ("flip", "blue", "blank") else "flip")
            if screen_id in explicit_ids:
                continue
        if not screen_id or screen_id in known_ids:
            continue
        known_ids.add(screen_id)
        base = default_by_id.get(
            screen_id,
            ScreenConfig(id=screen_id, stand_enabled=False, drive_enabled=False),
        ).model_dump()
        if was_legacy_clock:
            base["stand_enabled"] = base["drive_enabled"] = True
        for key in (
            "stand_enabled",
            "stand_duration_seconds",
            "drive_enabled",
            "drive_duration_seconds",
        ):
            if key in raw:
                base[key] = raw[key]
        if raw.get("enabled") is False:
            base["stand_enabled"] = False
            base["drive_enabled"] = False
        migrated_screens.append(base)

    for default_screen in DEFAULTS.screens:
        if default_screen.id not in known_ids:
            added = default_screen.model_dump()
            if raw_screens and default_screen.id.startswith("clock_"):
                added["stand_enabled"] = added["drive_enabled"] = False
            migrated_screens.append(added)

    if legacy_schema:
        default_order = {screen.id: index for index, screen in enumerate(DEFAULTS.screens)}
        migrated_screens.sort(
            key=lambda screen: default_order.get(screen["id"], len(default_order))
        )

    data["screens"] = migrated_screens or [s.model_dump() for s in DEFAULTS.screens]
    data["config_version"] = 8
    # Retired clock designs fall back without resetting unrelated settings.
    if data.get("theme") not in ("flip", "blue", "blank"):
        data["theme"] = "flip"
    data.setdefault("brightness_stand", 40)
    data.setdefault("brightness_drive", 100)
    # Preserve existing night shutoff until the user selects the new night clock.
    data.setdefault("night_behavior", "off")
    data.setdefault("panel_opacity_percent", 52)
    data.setdefault("panel_blur_pixels", 0)
    data.setdefault("drive_enter_speed_kmh", 8.0)
    data.setdefault("drive_enter_seconds", 10)
    data.setdefault("stand_enter_speed_kmh", 3.0)
    data.setdefault("stand_enter_seconds", 180)
    data.setdefault("gps_state_hold_seconds", 300)
    data.setdefault("vacations", [])
    data.setdefault("calendar_enabled", False)
    data.setdefault("calendar_url", "")
    data.setdefault("photo_frame_manual_seconds", 300)
    data.pop("brightness", None)
    data.pop("screen_interval_seconds", None)
    return data


def load_settings() -> Settings:
    conn = _connect()
    try:
        row = conn.execute("SELECT data FROM settings WHERE id = 1").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO settings (id, data) VALUES (1, ?)",
                (DEFAULTS.model_dump_json(),),
            )
            return DEFAULTS
        raw = json.loads(row[0])
        settings = Settings.model_validate(_migrate(raw))
        normalized = settings.model_dump(mode="json")
        if raw != normalized:
            conn.execute(
                "UPDATE settings SET data = ? WHERE id = 1",
                (settings.model_dump_json(),),
            )
        return settings
    finally:
        conn.close()


def save_settings(settings: Settings) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO settings (id, data) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (settings.model_dump_json(),),
        )
    finally:
        conn.close()


def load_calendar_cache(source: str) -> dict | None:
    conn = _connect()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS calendar_cache (id INTEGER PRIMARY KEY CHECK (id = 1), source TEXT NOT NULL, data TEXT NOT NULL)")
        row = conn.execute("SELECT data FROM calendar_cache WHERE id = 1 AND source = ?", (source,)).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()


def save_calendar_cache(source: str, data: dict) -> None:
    conn = _connect()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS calendar_cache (id INTEGER PRIMARY KEY CHECK (id = 1), source TEXT NOT NULL, data TEXT NOT NULL)")
        conn.execute(
            "INSERT INTO calendar_cache (id, source, data) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET source = excluded.source, data = excluded.data",
            (source, json.dumps(data, ensure_ascii=False)),
        )
    finally:
        conn.close()


def load_trip() -> tuple[float, float | None, float | None]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT total_km, last_lat, last_lon FROM trip WHERE id = 1"
        ).fetchone()
        return row[0], row[1], row[2]
    finally:
        conn.close()


def save_trip(total_km: float, last_lat: float | None, last_lon: float | None) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE trip SET total_km = ?, last_lat = ?, last_lon = ? WHERE id = 1",
            (total_km, last_lat, last_lon),
        )
    finally:
        conn.close()


def reset_trip() -> None:
    save_trip(0.0, None, None)


def load_trip_route() -> dict:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT start_lat, start_lon, dest_name, dest_lat, dest_lon FROM trip_route WHERE id = 1"
        ).fetchone()
        return {
            "start_lat": row[0],
            "start_lon": row[1],
            "dest_name": row[2],
            "dest_lat": row[3],
            "dest_lon": row[4],
        }
    finally:
        conn.close()


def save_trip_route(
    start_lat: float | None,
    start_lon: float | None,
    dest_name: str | None,
    dest_lat: float | None,
    dest_lon: float | None,
) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE trip_route SET start_lat = ?, start_lon = ?, dest_name = ?, dest_lat = ?, dest_lon = ? "
            "WHERE id = 1",
            (start_lat, start_lon, dest_name, dest_lat, dest_lon),
        )
    finally:
        conn.close()
