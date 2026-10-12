import os
import re
import subprocess
import threading
from datetime import datetime

import display_backlight
import operating_state
import settings_store

_CHECK_INTERVAL_SECONDS = 1
_HDMI_OUTPUT = "HDMI-1"
_TOUCH_DEVICE_NAME = "WaveShare"
_TOUCH_READ_CHUNK = 4096

_state = {"display_on": True, "manual_off": False, "brightness_control": "software"}
_power_lock = threading.RLock()


def _parse_hhmm(value: str) -> tuple[int, int] | None:
    try:
        hh, mm = value.split(":")
        hh, mm = int(hh), int(mm)
        return (hh, mm) if 0 <= hh < 24 and 0 <= mm < 60 else None
    except (ValueError, AttributeError):
        return None


def _in_off_window(now: datetime, off_time: str, on_time: str) -> bool:
    off = _parse_hhmm(off_time)
    on = _parse_hhmm(on_time)
    if off is None or on is None:
        return False

    now_minutes = now.hour * 60 + now.minute
    off_minutes = off[0] * 60 + off[1]
    on_minutes = on[0] * 60 + on[1]

    if off_minutes == on_minutes:
        return False
    if off_minutes < on_minutes:
        # Same-day window, e.g. 13:00-15:00
        return off_minutes <= now_minutes < on_minutes
    # Overnight window, e.g. 22:00-06:00
    return now_minutes >= off_minutes or now_minutes < on_minutes


def _set_display_power(turn_on: bool) -> None:
    if turn_on:
        args = ["xrandr", "--output", _HDMI_OUTPUT, "--rotate", "left", "--auto"]
    else:
        args = ["xrandr", "--output", _HDMI_OUTPUT, "--off"]
    result = subprocess.run(
        args,
        env={"DISPLAY": ":0"},
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Display-Schaltung fehlgeschlagen")
    _state["display_on"] = turn_on
    display_backlight.invalidate()
    _state["brightness_control"] = "software"


def force_display_power(turn_on: bool) -> None:
    """Manual off remains latched until Screen an or a service restart."""
    with _power_lock:
        _set_display_power(turn_on)
        _state["manual_off"] = not turn_on
        if turn_on:
            settings = settings_store.load_settings()
            operating_state.start_manual_wake(settings.night_wake_seconds)


def display_policy(settings, operating: dict, now: datetime, manual_off=False) -> dict:
    scheduled = (operating["mode"] == "stand" and settings.display_schedule_enabled
                 and _in_off_window(now, settings.display_off_time, settings.display_on_time))
    resting = scheduled and not operating["manual_wake_active"]
    night = resting and settings.night_behavior == "clock" and not manual_off
    on = not manual_off and not (resting and settings.night_behavior == "off")
    brightness = settings.brightness_night if night else (
        settings.brightness_drive if operating["mode"] == "drive" else settings.brightness_stand)
    return {"display_on": on, "night_clock_active": night,
            "brightness_percent": brightness, "manual_off": manual_off}


def wake_from_touch() -> bool:
    with _power_lock:
        settings = settings_store.load_settings()
        if not settings.touch_wake_enabled or _state["manual_off"]:
            return False
        operating = operating_state.get_status()
        policy = display_policy(settings, operating, datetime.now())
        if policy["night_clock_active"] or not policy["display_on"] or operating["manual_wake_active"]:
            seconds = settings.night_wake_seconds if settings.night_behavior == "clock" else settings.touch_wake_hold_seconds
            operating_state.start_manual_wake(seconds)
            if not _state["display_on"]:
                _set_display_power(True)
            return True
        return False


def get_status() -> dict:
    settings = settings_store.load_settings()
    operating = operating_state.get_status()
    result = display_policy(settings, operating, datetime.now(), _state["manual_off"])
    result["display_on"] = _state["display_on"]
    # Only report hardware success for the currently requested value.
    result["brightness_control"] = (_state["brightness_control"]
        if _state.get("applied_brightness") == result["brightness_percent"] else "software")
    return result


def _run_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        settings = settings_store.load_settings()
        with _power_lock:
            operating = operating_state.get_status()
            policy = display_policy(settings, operating, datetime.now(), _state["manual_off"])
            try:
                if policy["display_on"] != _state["display_on"]:
                    _set_display_power(policy["display_on"])
                hardware = display_backlight.apply(policy["brightness_percent"])
                _state["brightness_control"] = "hardware" if hardware else "software"
                _state["applied_brightness"] = policy["brightness_percent"]
            except (OSError, subprocess.SubprocessError, RuntimeError):
                # Keep retrying; a missing X display must not kill the scheduler.
                _state["brightness_control"] = "software"
        stop_event.wait(_CHECK_INTERVAL_SECONDS)


def _find_touch_device_path() -> str | None:
    try:
        content = open("/proc/bus/input/devices").read()
    except OSError:
        return None

    for block in content.split("\n\n"):
        if _TOUCH_DEVICE_NAME.lower() not in block.lower():
            continue
        match = re.search(r"Handlers=.*?(event\d+)", block)
        if match:
            return f"/dev/input/{match.group(1)}"
    return None


def _touch_watch_loop(stop_event: threading.Event) -> None:
    device_path = None
    fd = None

    while not stop_event.is_set():
        settings = settings_store.load_settings()
        if not settings.touch_wake_enabled:
            if fd is not None:
                os.close(fd)
                fd = None
            stop_event.wait(5)
            continue

        if fd is None:
            device_path = device_path or _find_touch_device_path()
            if device_path is None:
                stop_event.wait(10)
                continue
            try:
                fd = os.open(device_path, os.O_RDONLY | os.O_NONBLOCK)
            except OSError:
                fd = None
                stop_event.wait(10)
                continue

        try:
            data = os.read(fd, _TOUCH_READ_CHUNK)
        except BlockingIOError:
            data = b""
        except OSError:
            os.close(fd)
            fd = None
            device_path = None
            stop_event.wait(2)
            continue

        if data:
            try:
                wake_from_touch()
            except (OSError, subprocess.SubprocessError, RuntimeError):
                pass

        stop_event.wait(0.3)

    if fd is not None:
        os.close(fd)


def start_background_thread() -> threading.Event:
    stop_event = threading.Event()
    thread = threading.Thread(target=_run_loop, args=(stop_event,), daemon=True)
    thread.start()
    return stop_event


def start_touch_watch_thread() -> threading.Event:
    stop_event = threading.Event()
    thread = threading.Thread(target=_touch_watch_loop, args=(stop_event,), daemon=True)
    thread.start()
    return stop_event
