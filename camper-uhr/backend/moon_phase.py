import math
from datetime import datetime, timezone

# Known new moon reference epoch and the synodic (new-moon-to-new-moon) month
# length. Accurate to roughly +/-1 day, which is plenty for a display.
_REFERENCE_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
_SYNODIC_MONTH_DAYS = 29.53058867

_PHASES = [
    ("Neumond", "🌑"),
    ("Zunehmende Sichel", "🌒"),
    ("Erstes Viertel", "🌓"),
    ("Zunehmender Dreiviertelmond", "🌔"),
    ("Vollmond", "🌕"),
    ("Abnehmender Dreiviertelmond", "🌖"),
    ("Letztes Viertel", "🌗"),
    ("Abnehmende Sichel", "🌘"),
]


def phase_from_fraction(fraction: float) -> dict:
    fraction %= 1.0
    illumination_pct = (1 - math.cos(2 * math.pi * fraction)) / 2 * 100
    name, emoji = _PHASES[round(fraction * 8) % 8]

    return {
        "phase_name": name,
        "emoji": emoji,
        "illumination_pct": round(illumination_pct, 1),
        "phase_fraction": round(fraction, 4),
    }


def current_phase() -> dict:
    days_since = (datetime.now(timezone.utc) - _REFERENCE_NEW_MOON).total_seconds() / 86400
    fraction = (days_since % _SYNODIC_MONTH_DAYS) / _SYNODIC_MONTH_DAYS
    return phase_from_fraction(fraction)
