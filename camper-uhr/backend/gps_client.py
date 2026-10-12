import json
from collections import deque
from statistics import median
import math
import socket
import threading
import time

import settings_store

_lock = threading.Lock()
_real_latest = {
    "connected": False,
    "latitude": None,
    "longitude": None,
    "speed_kmh": None,
    "altitude_m": None,
    "altitude_reference": None,
    "heading_deg": None,
}
_simulated_latest = {
    "connected": False,
    "latitude": None,
    "longitude": None,
    "speed_kmh": None,
    "altitude_m": None,
    "altitude_reference": None,
    "heading_deg": None,
}
_simulation_active = False

# In-memory breadcrumb trail (never persisted to disk): throttled to at most
# one point every 10s to keep it small. Lost on restart by design - a fresh
# trail after every power cycle, not a permanent log. Duration/on-off are
# user-configurable in Settings (map_trail_enabled / map_trail_max_hours).
_TRAIL_MIN_INTERVAL_SECONDS = 10
_trail: list[tuple[float, float, float]] = []


def _record_trail_point(lat: float, lon: float) -> None:
    settings = settings_store.load_settings()
    if not settings.map_trail_enabled:
        return

    now = time.time()
    with _lock:
        if _trail and now - _trail[-1][0] < _TRAIL_MIN_INTERVAL_SECONDS:
            return
        _trail.append((now, lat, lon))
        cutoff = now - settings.map_trail_max_hours * 3600
        while _trail and _trail[0][0] < cutoff:
            _trail.pop(0)


def get_trail() -> list[dict]:
    if not settings_store.load_settings().map_trail_enabled:
        return []
    with _lock:
        return [{"latitude": lat, "longitude": lon} for _, lat, lon in _trail]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _finite_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class MotionFilter:
    """Bounded, time-based rejection of GPS speed/course jitter; RAM only."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.samples = deque(maxlen=5)
        self.courses = deque(maxlen=3)
        self.moving = False
        self.since = None
        self.speed = 0.0
        self.heading = None
        self.last = None

    def update(self, speed, heading, now):
        if self.last is not None and (now - self.last > 5 or now < self.last):
            self.reset()
        dt = max(0.0, now - self.last) if self.last is not None else 0.0
        self.last = now
        if speed is None or not math.isfinite(speed) or speed < 0:
            self.reset()
            return None, None
        self.samples.append((now, speed))
        while self.samples and now - self.samples[0][0] > 4:
            self.samples.popleft()
        value = median(v for _, v in self.samples)
        if len(self.samples) < 3:
            return 0.0, None
        if not self.moving:
            if value >= 4:
                if self.since is None:
                    self.since = now
                if now - self.since >= 2:
                    self.moving = True
                    self.speed = value
            else:
                self.since = None
        elif value < 2:
            self.moving = False
            self.since = None
        if not self.moving:
            self.speed = 0.0
            self.heading = None
            self.courses.clear()
            return 0.0, None
        self.speed += (1 - math.exp(-dt / 1.0)) * (value - self.speed)
        if heading is None or not math.isfinite(heading) or not 0 <= heading < 360:
            self.heading = None
            self.courses.clear()
            return self.speed, None
        if value < 5 or speed < 5:
            return self.speed, self.heading
        self.courses.append(heading)
        # Circular medoid rejects an isolated course spike, including around north.
        delta = lambda a, b: (a - b + 180) % 360 - 180
        target = min(self.courses, key=lambda a: sum(abs(delta(a,b)) for b in self.courses))
        if self.heading is None:
            self.heading = target
        else:
            self.heading = (self.heading + (1 - math.exp(-dt / 1.2)) * delta(target,self.heading)) % 360
        return self.speed, self.heading


_motion_filter = MotionFilter()


def _altitude_from_report(report: dict) -> tuple[float | None, str | None]:
    if report.get("mode") != 3:
        return None, None
    altitude_msl = _finite_float(report.get("altMSL"))
    if altitude_msl is not None:
        return altitude_msl, "msl"
    altitude_hae = _finite_float(report.get("altHAE"))
    if altitude_hae is not None:
        return altitude_hae, "hae"
    return None, None


def _handle_fix(
    lat: float,
    lon: float,
    speed_ms: float | None,
    altitude_m: float | None,
    altitude_reference: str | None,
    heading_deg: float | None = None,
) -> None:
    with _lock:
        _real_latest["connected"] = True
        _real_latest["latitude"] = lat
        _real_latest["longitude"] = lon
        speed = _finite_float(speed_ms)
        filtered_speed, filtered_heading = _motion_filter.update(
            None if speed is None else speed * 3.6,
            _finite_float(heading_deg), time.monotonic(),
        )
        _real_latest["speed_kmh"] = filtered_speed
        _real_latest["heading_deg"] = filtered_heading
        altitude = _finite_float(altitude_m)
        _real_latest["altitude_m"] = altitude
        _real_latest["altitude_reference"] = altitude_reference if altitude is not None else None
        simulation_active = _simulation_active
    if not simulation_active:
        _record_trail_point(lat, lon)


def set_simulated_fix(
    lat: float,
    lon: float,
    speed_kmh: float = 0.0,
    altitude_m: float | None = None,
    heading_deg: float | None = None,
) -> None:
    """Testing helper: override the current position without touching the
    trip odometer, e.g. to preview the map/weather screens without a live
    GPS fix from the router."""
    global _simulation_active
    with _lock:
        _simulation_active = True
        _simulated_latest["connected"] = True
        _simulated_latest["latitude"] = lat
        _simulated_latest["longitude"] = lon
        _simulated_latest["speed_kmh"] = speed_kmh
        heading = _finite_float(heading_deg)
        _simulated_latest["heading_deg"] = (
            heading if heading is not None and 0 <= heading < 360 and speed_kmh >= 3 else None
        )
        altitude = _finite_float(altitude_m)
        _simulated_latest["altitude_m"] = altitude
        _simulated_latest["altitude_reference"] = "msl" if altitude is not None else None
    _record_trail_point(lat, lon)


def clear_simulated_fix() -> None:
    """End simulation and return to the latest real router-GPS state."""
    global _simulation_active
    with _lock:
        _simulation_active = False


def _mark_disconnected() -> None:
    with _lock:
        _real_latest["connected"] = False
        _motion_filter.reset()
        _real_latest["heading_deg"] = None


def _run_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        settings = settings_store.load_settings()
        if not settings.gpsd_host.strip():
            _mark_disconnected()
            stop_event.wait(5)
            continue
        try:
            with socket.create_connection(
                (settings.gpsd_host, settings.gpsd_port), timeout=5
            ) as sock:
                sock.sendall(b'?WATCH={"enable":true,"json":true}\n')
                buf = b""
                sock.settimeout(10)
                while not stop_event.is_set():
                    chunk = sock.recv(4096)
                    if not chunk:
                        _mark_disconnected()
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        _process_line(line)
        except (OSError, socket.timeout):
            _mark_disconnected()
            stop_event.wait(5)


def _process_line(line: bytes) -> None:
    try:
        report = json.loads(line)
    except json.JSONDecodeError:
        return
    if report.get("class") == "TPV" and report.get("mode", 2) < 2:
        _mark_disconnected()
        return
    if report.get("class") == "TPV" and "lat" in report and "lon" in report:
        altitude_m, altitude_reference = _altitude_from_report(report)
        _handle_fix(
            report["lat"],
            report["lon"],
            report.get("speed"),
            altitude_m,
            altitude_reference,
            report.get("track"),
        )


def _route_status(current_lat: float | None, current_lon: float | None) -> dict:
    route = settings_store.load_trip_route()
    start_lat, start_lon = route["start_lat"], route["start_lon"]
    dest_lat, dest_lon = route["dest_lat"], route["dest_lon"]

    has_route = None not in (start_lat, start_lon, dest_lat, dest_lon)
    if not has_route:
        return {"has_route": False, "progress": 0.0, "start_label": None, "dest_label": route["dest_name"]}

    total = _haversine_km(start_lat, start_lon, dest_lat, dest_lon)
    if total < 0.01 or current_lat is None or current_lon is None:
        progress = 0.0
    else:
        travelled = _haversine_km(start_lat, start_lon, current_lat, current_lon)
        progress = max(0.0, min(1.0, travelled / total))

    return {
        "has_route": True,
        "progress": progress,
        "start_label": "Start",
        "dest_label": route["dest_name"],
    }


def get_status() -> dict:
    with _lock:
        latest = dict(_simulated_latest if _simulation_active else _real_latest)
        simulation_active = _simulation_active
    total_km, _, _ = settings_store.load_trip()
    return {
        "connected": latest["connected"],
        "latitude": latest["latitude"],
        "longitude": latest["longitude"],
        "speed_kmh": latest["speed_kmh"],
        "altitude_m": latest["altitude_m"],
        "altitude_reference": latest["altitude_reference"],
        "heading_deg": latest.get("heading_deg") if latest["connected"] else None,
        "trip_km": total_km,
        "route": _route_status(latest["latitude"], latest["longitude"]),
        "simulation_active": simulation_active,
    }


def start_background_thread() -> threading.Event:
    stop_event = threading.Event()
    thread = threading.Thread(target=_run_loop, args=(stop_event,), daemon=True)
    thread.start()
    return stop_event
