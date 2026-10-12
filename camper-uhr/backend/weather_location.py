"""Resolve the weather request's location in the background, with bounded RAM cache."""
from collections import OrderedDict
import threading
import time

from arrival_provider import clean, get_json


def resolve(lat, lon):
    payload = get_json('https://nominatim.openstreetmap.org/reverse',
                       lat=lat, lon=lon, format='jsonv2', zoom=10,
                       addressdetails=1, **{'accept-language': 'de'})
    address = payload.get('address') or {}
    town = next((clean(address[k]) for k in
                 ('city', 'town', 'village', 'municipality', 'hamlet') if address.get(k)), '')
    town = town or clean(payload.get('name'))
    country = clean(address.get('country'))
    return ' · '.join(dict.fromkeys(s for s in (town, country) if s))[:160] if town else None


class LocationNames:
    def __init__(self):
        self.lock = threading.Lock()
        self.cache = OrderedDict()
        self.pending = None

    def get(self, lat, lon):
        key = (lat, lon)
        with self.lock:
            entry = self.cache.get(key)
            if entry and entry[1] > time.monotonic():
                self.cache.move_to_end(key)
                return entry[0]
            if self.pending is None:
                self.pending = key
                threading.Thread(target=self._fetch, args=(key,), daemon=True).start()
        return None

    def _fetch(self, key):
        try:
            name = resolve(*key)
        except Exception:
            name = None
        with self.lock:
            self.cache[key] = (name, time.monotonic() + (86400 if name else 600))
            self.cache.move_to_end(key)
            while len(self.cache) > 8:
                self.cache.popitem(last=False)
            self.pending = None


names = LocationNames()


def annotate(weather):
    lat, lon = weather.get('latitude'), weather.get('longitude')
    if lat is None or lon is None:
        return weather
    # Return a snapshot; the worker never mutates a weather response or its cache.
    return {**weather, 'location_name': names.get(lat, lon)}
