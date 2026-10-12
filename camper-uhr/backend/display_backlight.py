"""Optional, explicitly configured Linux backlight; no probing or system changes.

Set CAMPERDISPLAY_BACKLIGHT_DIR to the verified /sys/class/backlight/<device>
directory only after checking the physical display. Otherwise use UI dimming.
"""
import os
from pathlib import Path

_applied = None


def apply(percent: int) -> bool:
    global _applied
    directory = os.environ.get("CAMPERDISPLAY_BACKLIGHT_DIR", "")
    if not directory:
        return False
    device = Path(directory)
    if device.parent != Path('/sys/class/backlight') or not device.name:
        return False
    try:
        maximum = int((device / 'max_brightness').read_text().strip())
        if maximum < 1:
            return False
        target = max(1, round(maximum * max(1, min(100, percent)) / 100))
        if _applied != (directory, target):
            (device / 'brightness').write_text(str(target))
            _applied = (directory, target)
        return True
    except (OSError, ValueError):
        _applied = None
        return False


def invalidate():
    global _applied
    _applied = None
