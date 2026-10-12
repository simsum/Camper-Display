"""Ephemeral manual presentation state for the local photo frame."""
import threading
import time

_lock = threading.Lock()
_active_until = 0.0


def show(seconds: int) -> dict:
    global _active_until
    with _lock:
        _active_until = time.time() + max(30, min(3600, int(seconds)))
        return status()


def hide() -> dict:
    global _active_until
    with _lock:
        _active_until = 0.0
        return {"active": False, "remaining_seconds": 0}


def status() -> dict:
    remaining = max(0, round(_active_until - time.time()))
    return {"active": remaining > 0, "remaining_seconds": remaining}
