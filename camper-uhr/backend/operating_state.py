import math
import threading
import time

import gps_client
import settings_store


class StateEngine:
    def __init__(self) -> None:
        self.mode = "stand"
        self.forced_mode: str | None = None
        self.gps_connected = False
        self.speed_kmh: float | None = None
        self._drive_since: float | None = None
        self._stand_since: float | None = None
        self._gps_missing_since: float | None = None
        self._manual_wake_until = 0.0

    def update(self, connected: bool, speed_kmh: float | None, settings, now: float) -> None:
        valid_speed = (
            connected
            and speed_kmh is not None
            and math.isfinite(speed_kmh)
            and speed_kmh >= 0
        )
        self.gps_connected = bool(valid_speed)
        self.speed_kmh = speed_kmh if valid_speed else None

        if not valid_speed:
            self._drive_since = None
            self._stand_since = None
            if self._gps_missing_since is None:
                self._gps_missing_since = now
            if (
                self.mode == "drive"
                and now - self._gps_missing_since >= settings.gps_state_hold_seconds
            ):
                self.mode = "stand"
            return

        self._gps_missing_since = None

        if speed_kmh >= settings.drive_enter_speed_kmh:
            if self._drive_since is None:
                self._drive_since = now
            if now - self._drive_since >= settings.drive_enter_seconds:
                self.mode = "drive"
        else:
            self._drive_since = None

        if speed_kmh < settings.stand_enter_speed_kmh:
            if self._stand_since is None:
                self._stand_since = now
            if now - self._stand_since >= settings.stand_enter_seconds:
                self.mode = "stand"
        else:
            self._stand_since = None

    def set_forced_mode(self, mode: str | None) -> None:
        self.forced_mode = mode

    def start_manual_wake(self, seconds: int, now: float) -> None:
        self._manual_wake_until = now + seconds

    def snapshot(self, now: float) -> dict:
        wake_remaining = max(0, math.ceil(self._manual_wake_until - now))
        return {
            "mode": self.forced_mode or self.mode,
            "forced_mode": self.forced_mode,
            "gps_connected": self.gps_connected,
            "speed_kmh": self.speed_kmh,
            "manual_wake_active": wake_remaining > 0,
            "manual_wake_remaining_seconds": wake_remaining,
        }


_engine = StateEngine()
_lock = threading.Lock()


def update_from_gps(now: float | None = None) -> None:
    settings = settings_store.load_settings()
    gps = gps_client.get_status()
    with _lock:
        _engine.update(
            connected=gps["connected"],
            speed_kmh=gps["speed_kmh"],
            settings=settings,
            now=time.monotonic() if now is None else now,
        )


def get_status(now: float | None = None) -> dict:
    with _lock:
        return _engine.snapshot(time.monotonic() if now is None else now)


def set_forced_mode(mode: str | None) -> None:
    with _lock:
        _engine.set_forced_mode(mode)


def start_manual_wake(seconds: int) -> None:
    with _lock:
        _engine.start_manual_wake(seconds, time.monotonic())


def _run_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        update_from_gps()
        stop_event.wait(1)


def start_background_thread() -> threading.Event:
    stop_event = threading.Event()
    thread = threading.Thread(target=_run_loop, args=(stop_event,), daemon=True)
    thread.start()
    return stop_event
