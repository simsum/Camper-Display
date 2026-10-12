"""Read-only iCloud vacation feed; network work never runs in the display request."""
import copy
import hashlib
import threading
import time
from datetime import date, datetime, time as daytime, timedelta, timezone
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx
from icalendar import Calendar
import recurring_ical_events

import settings_store
from calendar_url import normalize_calendar_url
from models import VacationConfig

REFRESH_SECONDS = 15 * 60
MAX_BYTES = 1024 * 1024
_lock = threading.Lock()
_refresh = threading.Event()
_source = ""
_state = {}


def source_key(url):
    return hashlib.sha256(url.encode()).hexdigest()


def calendar_timezone(calendar):
    name = str(calendar.get("X-WR-TIMEZONE", ""))
    if name:
        return ZoneInfo(name)
    try:
        with open("/etc/localtime", "rb") as stream:
            return ZoneInfo.from_file(stream)
    except OSError:
        return ZoneInfo("Europe/Berlin")


def parse_calendar(payload: bytes, today: date | None = None) -> list[dict]:
    if len(payload) > MAX_BYTES:
        raise ValueError("Kalender ist zu groß")
    calendar = Calendar.from_ical(payload)
    if calendar.name != "VCALENDAR":
        raise ValueError("Kein Kalender")
    events = calendar.walk("VEVENT")
    if len(events) > 2000:
        raise ValueError("Zu viele Kalendereinträge")
    for event in events:
        if event.errors or "DTSTART" not in event or "UID" not in event:
            raise ValueError("Unvollständiger Kalendereintrag")
        rule = event.get("RRULE")
        if rule and str(rule.get("FREQ", [""])[0]) not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"):
            raise ValueError("Zu häufige Wiederholung")
    tz = calendar_timezone(calendar)
    today = today or datetime.now(tz).date()
    # Include the previous year (overlapping trips) and two full future years.
    first = datetime(today.year - 1, 1, 1, tzinfo=tz)
    stop = datetime(today.year + 3, 1, 1, tzinfo=tz)
    trips = {}
    for index, event in enumerate(recurring_ical_events.of(calendar).after(first)):
        if index >= 10000:
            raise ValueError("Zu viele Wiederholungen")
        start = event.decoded("DTSTART")
        end = event.decoded("DTEND", None)
        if isinstance(start, datetime):
            start = start.replace(tzinfo=tz) if start.tzinfo is None else start.astimezone(tz)
            if start >= stop:
                break
            if end is None:
                end = start
            if not isinstance(end, datetime):
                raise ValueError("Uneinheitlicher Terminzeitraum")
            end = end.replace(tzinfo=tz) if end.tzinfo is None else end.astimezone(tz)
            if end < start:
                raise ValueError("Ungültiger Terminzeitraum")
            start_day = start.date()
            end_day = end.date()
            if end > start and end.timetz().replace(tzinfo=None) == daytime.min:
                end_day -= timedelta(days=1)
        else:
            if start >= stop.date():
                break
            start_day = start
            # iCalendar all-day DTEND is exclusive; our vacation end is inclusive.
            end_day = end - timedelta(days=1) if end else start
            if end_day < start_day:
                end_day = start_day
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        uid = str(event.get("UID"))
        recurrence = str(event.get("RECURRENCE-ID", start))
        identity = "icloud-" + hashlib.sha256(f"{uid}|{recurrence}".encode()).hexdigest()[:48]
        trip = VacationConfig(
            id=identity,
            name=(str(event.get("SUMMARY", "Urlaub")).strip() or "Urlaub")[:80],
            destination=" ".join(str(event.get("LOCATION", "")).split())[:120],
            start_date=start_day,
            end_date=end_day,
        )
        trips[identity] = trip.model_dump(mode="json")
    return sorted(trips.values(), key=lambda item: (item["start_date"], item["id"]))


def download_calendar(url: str) -> bytes:
    url = normalize_calendar_url(url)
    deadline = time.monotonic() + 30
    with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client:
        for _ in range(4):
            with client.stream("GET", url, headers={"Accept": "text/calendar"}) as response:
                if response.is_redirect:
                    url = normalize_calendar_url(urljoin(url, response.headers.get("location", "")))
                    continue
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_BYTES or time.monotonic() > deadline:
                        raise ValueError("Kalenderabruf überschreitet die Begrenzung")
                return bytes(data)
    raise ValueError("Zu viele Weiterleitungen")


def get_status(settings=None):
    settings = settings or settings_store.load_settings()
    if not settings.calendar_enabled or not settings.calendar_url:
        return {"enabled": False, "state": "disabled", "vacations": []}
    with _lock:
        if _source != source_key(settings.calendar_url):
            return {"enabled": True, "state": "loading", "vacations": []}
        result = copy.deepcopy(_state)
    result["enabled"] = True
    return result


def request_refresh():
    _refresh.set()


def sync_calendar(settings):
    global _source, _state
    source = source_key(settings.calendar_url)
    with _lock:
        changed = source != _source
    if changed:
        cached = settings_store.load_calendar_cache(source)
        with _lock:
            _source = source
            _state = {**(cached or {"vacations": []}), "state": "loading", "stale": bool(cached)}
    try:
        trips = parse_calendar(download_calendar(settings.calendar_url))
        state = {
            "state": "ready", "stale": False, "vacations": trips,
            "last_success": datetime.now(timezone.utc).isoformat(),
        }
        # A removed or replaced feed must not publish an in-flight result.
        current = settings_store.load_settings()
        if not current.calendar_enabled or current.calendar_url != settings.calendar_url:
            return
        settings_store.save_calendar_cache(source, state)
        with _lock:
            _state = state
    except Exception:
        # Never include exception text: HTTP/parser errors may contain the secret link.
        with _lock:
            _state = {**_state, "state": "error", "stale": bool(_state.get("last_success")),
                      "message": "Kalender nicht aktualisiert. Internetverbindung und Freigabelink prüfen."}


def start_background_thread():
    stop = threading.Event()

    def run():
        previous = None
        next_refresh = 0
        while not stop.is_set():
            try:
                settings = settings_store.load_settings()
                key = (settings.calendar_enabled, settings.calendar_url)
                if settings.calendar_enabled and settings.calendar_url:
                    if key != previous or _refresh.is_set() or time.monotonic() >= next_refresh:
                        _refresh.clear()
                        sync_calendar(settings)
                        next_refresh = time.monotonic() + REFRESH_SECONDS
                previous = key
            except Exception:
                pass  # A feed/storage failure must never stop the clock or the worker.
            stop.wait(2)

    threading.Thread(target=run, name="icloud-calendar", daemon=True).start()
    return stop
