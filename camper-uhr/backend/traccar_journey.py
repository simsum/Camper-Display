"""Bounded on-demand trip preview, no persistent location history."""
import json
import hashlib
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from urllib.parse import urlencode
import traccar_client as client

LOCK = threading.Lock()


def moment(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            return None
        return result.astimezone(timezone.utc)
    except (ValueError, AttributeError, TypeError):
        return None


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def vacations():
    path = Path(os.environ.get("CAMPERDISPLAY_VACATION_DB", client.DB_PATH.parent / "camperdisplay.db"))
    result = []
    if not path.exists():
        return result
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        row = db.execute("SELECT data FROM settings WHERE id=1").fetchone()
        settings = json.loads(row[0]) if row else {}
        rows = settings.get("vacations", [])
        # Only an existing cache, never trigger calendar network requests here.
        if settings.get("calendar_enabled"):
            try:
                source = hashlib.sha256(settings.get("calendar_url", "").encode()).hexdigest()
                cached = db.execute("SELECT data FROM calendar_cache WHERE id=1 AND source=?", (source,)).fetchone()
                if cached:
                    rows += json.loads(cached[0]).get("vacations", [])
            except sqlite3.OperationalError:
                pass
        for item in rows:
            if item.get("enabled", True):
                try:
                    start = date.fromisoformat(item["start_date"])
                    end = date.fromisoformat(item["end_date"])
                    if end >= start:
                        result.append({"name": str(item.get("name", "Urlaub"))[:80], "start": str(start), "end": str(end)})
                except (KeyError, TypeError, ValueError):
                    pass
        return result[:200]
    except (sqlite3.Error, ValueError):
        return []
    finally:
        db.close()


def report(config, kind, start, end):
    query = urlencode({"deviceId": config["device_id"], "from": iso(start), "to": iso(end)})
    value = client.fetch_json(config, f"/reports/{kind}?{query}", max_bytes=8_000_000, timeout=45)
    if not isinstance(value, list):
        raise client.TraccarError("Unerwartete Fahrbericht-Antwort.")
    return [row for row in value if isinstance(row, dict) and row.get("deviceId") == config["device_id"]]


def intervals(rows, start, end):
    result = []
    for row in rows:
        a, b = moment(row.get("startTime")), moment(row.get("endTime"))
        if a and b and b > a and a < end and b > start:
            result.append((max(a, start), min(b, end), row))
    return sorted(result, key=lambda item: item[0])


def seconds_union(items):
    total = 0
    last = None
    for a, b, *_ in sorted(items, key=lambda item: item[0]):
        if last is not None:
            a = max(a, last)
        total += max(0, (b - a).total_seconds())
        last = max(last, b) if last else b
    return round(total)


def route_segments(rows):
    points = []
    for row in rows:
        lat, lon = client.number(row.get("latitude")), client.number(row.get("longitude"))
        time = moment(row.get("fixTime"))
        if row.get("valid") is True and lat is not None and lon is not None and abs(lat) <= 85 and abs(lon) <= 180 and time:
            points.append((time, round(lat, 6), round(lon, 6)))
    points.sort()
    segments = []
    previous = None
    for time, lat, lon in points:
        if previous is None or (time - previous[0]).total_seconds() > 900 or abs(lon - previous[2]) > 180:
            segments.append([])
        if not segments[-1] or segments[-1][-1] != [lat, lon]:
            segments[-1].append([lat, lon])
        previous = (time, lat, lon)
    # Preserve all segment boundaries; fail explicitly rather than bridge gaps.
    if len(segments) > 200:
        raise client.TraccarError("Zu viele GPS-Unterbrechungen. Bitte einen kürzeren Zeitraum wählen.")
    count = sum(map(len, segments))
    target = 1200 - 2 * len(segments)
    reduced = []
    for segment in segments:
        budget = min(len(segment), max(2, int(target * len(segment) / max(1, count)) + 2))
        reduced.append([segment[round(i * (len(segment) - 1) / max(1, budget - 1))] for i in range(budget)])
    return reduced, count


def validate_payload(payload):
    if not isinstance(payload,dict) or payload.get("mode") not in ("today","last","vacation"):
        raise client.TraccarError("Bitte einen Zeitraum auswählen.")
    mode=payload["mode"]
    if mode!="vacation":return {"mode":mode}
    start,end=moment(payload.get("from")),moment(payload.get("to"))
    if not start or not end or end<=start or end-start>timedelta(days=93):
        raise client.TraccarError("Bitte einen gültigen Zeitraum von höchstens 93 Tagen wählen.")
    return {"mode":mode,"from":iso(start),"to":iso(end)}


def journey(payload, now=None, config=None):
    """Slow work: only called by the single background worker (or diagnostics)."""
    import time
    import traccar_motion as motion
    import traccar_route_data as routes
    payload=validate_payload(payload)
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    deadline=time.monotonic()+120
    config=config or client.load_private()
    if not config["token"] or not config["device_id"]:
        raise client.TraccarError("Bitte zuerst Traccar-Zugang und Fahrzeug speichern.")
    devices=client.fetch_json(config,"/devices")
    device=next((d for d in devices if isinstance(d,dict) and d.get("id")==config["device_id"]),None) if isinstance(devices,list) else None
    if not device:raise client.TraccarError("Das gespeicherte Fahrzeug ist nicht freigegeben.")
    mode=payload["mode"]
    start,end=None,now
    if mode=="last":
        midnight=now.replace(hour=0,minute=0,second=0,microsecond=0)
        for offset in range(31):
            date_start=midnight-timedelta(days=offset)
            points=routes.day(config,date_start,now,deadline)
            found=motion.analyze(points)
            if not found["empty"]:
                end=datetime.fromtimestamp(found["to"],timezone.utc)
                start=end-timedelta(hours=24)
                break
        if start is None:
            return {"mode":mode,"empty":True,"message":"Keine Bewegung in den letzten 30 Tagen erkannt.","loaded_at":iso(now),"segments":[],"stops":[],"warnings":[]}
    elif mode=="today":
        start=datetime.combine(now.astimezone().date(),datetime.min.time()).astimezone(timezone.utc)
    else:
        start,end=moment(payload["from"]),min(moment(payload["to"]),now)
    if start>=end:raise client.TraccarError("Dieser Zeitraum liegt noch in der Zukunft.")
    points=routes.window(config,start,end,now,deadline)
    data=motion.analyze(points)
    base={"mode":mode,"window_from":iso(start),"window_to":iso(end),"loaded_at":iso(datetime.now(timezone.utc)),
          "segments":[],"stops":[],"warnings":[],"empty":data["empty"],"device_name":str(device.get("name","Camper"))[:120]}
    if data["empty"]:return {**base,"message":"In diesem Zeitraum wurde keine Bewegung erkannt."}
    try:segments=motion.simplify(data["segments"])
    except ValueError:raise client.TraccarError("Zu viele GPS-Unterbrechungen. Bitte Zeitraum verkürzen.") from None
    base.update({k:data[k] for k in ("drive_seconds","pause_seconds","unknown_seconds","distance_km","trip_count")})
    base.update({"from":iso(datetime.fromtimestamp(data["from"],timezone.utc)),"to":iso(datetime.fromtimestamp(data["to"],timezone.utc)),
                 "segments":segments,"source_points":len(points),"stop_count":len(data["stops"]),"stops":data["stops"][:100],
                 "start_address":"Erste Abfahrt im Zeitfenster","end_address":"Letzte Ankunft im Zeitfenster",
                 "average_kmh":round(data["distance_km"]/(data["drive_seconds"]/3600),1) if data["drive_seconds"] and not data["unknown_seconds"] and not data["distance_incomplete"] else None,
                 "metrics_source":"GPS-Auswertung · Pause ab 3 Min. unter 3 km/h"})
    if data["unknown_seconds"]:base["warnings"].append(f"{round(data['unknown_seconds']/60)} Min. ohne ausreichende GPS-Daten; nicht als Fahrzeit gezählt.")
    if any(s["estimated"] for s in data["stops"]):base["warnings"].append("Pausendauer aus zeitlich weit auseinanderliegenden Stillstandspunkten geschätzt.")
    if data["distance_estimated"]:base["warnings"].append("Teile der Strecke aus GPS-Punktabständen geschätzt.")
    if data["distance_incomplete"]:base["warnings"].append("Strecke wegen GPS-Lücken unvollständig.")
    return base
