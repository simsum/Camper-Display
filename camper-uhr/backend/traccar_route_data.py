"""Bounded in-memory, per-UTC-day route cache. No disk history or credentials in keys."""
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import threading
import time
from urllib.parse import urlencode
import traccar_client as client
from traccar_motion import compact

MAX_POINTS=150_000
_cache=OrderedDict()
_lock=threading.Lock()


def fingerprint(config):
    return hashlib.sha256(json.dumps([config["api_url"],config["device_id"],config["token"]]).encode()).hexdigest()


def reset():
    with _lock:_cache.clear()


def fetch_chunk(config,start,end,deadline):
    if time.monotonic()>deadline:raise client.TraccarError("Hintergrundabruf hat das Zeitlimit erreicht. Bitte kürzeren Zeitraum wählen.")
    query=urlencode({"deviceId":config["device_id"],"from":start.isoformat(),"to":end.isoformat()})
    try:
        rows=client.fetch_json(config,"/positions?"+query,max_bytes=32_000_000,timeout=15)
    except client.TraccarTooLarge:
        if (end-start).total_seconds()<1800:raise
        middle=start+(end-start)/2
        return fetch_chunk(config,start,middle,deadline)+fetch_chunk(config,middle,end,deadline)
    if not isinstance(rows,list):raise client.TraccarError("Unerwartete Positionsantwort.")
    return compact(r for r in rows if isinstance(r,dict) and r.get("deviceId")==config["device_id"])


def day(config,day_start,now,deadline):
    key=(fingerprint(config),day_start.date().isoformat())
    ttl=300 if day_start.date()==now.date() else 1800
    with _lock:
        value=_cache.get(key)
        if value and time.monotonic()-value[0]<ttl:
            _cache.move_to_end(key)
            return value[1]
    points=fetch_chunk(config,day_start,min(day_start+timedelta(days=1),now),deadline)
    points=[p for p in points if day_start.timestamp()<=p[0]<=min(day_start+timedelta(days=1),now).timestamp()]
    if len(points)>MAX_POINTS:raise client.TraccarError("Zu viele GPS-Punkte für einen Tag.")
    with _lock:
        _cache[key]=(time.monotonic(),points)
        _cache.move_to_end(key)
        while len(_cache)>40 or sum(len(v[1]) for v in _cache.values())>MAX_POINTS:
            _cache.popitem(last=False)
    return points


def window(config,start,end,now,deadline):
    cursor=start.replace(hour=0,minute=0,second=0,microsecond=0)
    result={}
    while cursor<end:
        for point in day(config,cursor,now,deadline):
            if start.timestamp()<=point[0]<=end.timestamp():result[point[0]]=point
        if len(result)>MAX_POINTS:raise client.TraccarError("Zeitraum enthält zu viele GPS-Punkte. Bitte verkürzen.")
        cursor+=timedelta(days=1)
    return sorted(result.values())
