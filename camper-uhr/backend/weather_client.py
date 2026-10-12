import time

import httpx
import weather_location

_cache: dict = {"expires_at": 0.0, "data": None}
_CACHE_SECONDS = 2 * 60 * 60

_EMPTY = {
    "available": False,
    "temperature": None,
    "apparent_temperature": None,
    "precipitation": None,
    "wind_speed": None,
    "condition_code": None,
    "unit_celsius": True,
    "forecast": [],
    "sunrise": None,
    "sunset": None,
    "daylight_duration_seconds": None,
    "moonrise": None,
    "moonset": None,
    "moon_phase_fraction": None,
}


def get_weather(lat: float | None, lon: float | None, celsius: bool) -> dict:
    if lat is None or lon is None:
        return {**_EMPTY, "unit_celsius": celsius}

    now = time.time()
    if _cache["data"] is not None and _cache["expires_at"] > now:
        cached = _cache["data"]
        if cached["unit_celsius"] == celsius:
            return weather_location.annotate(cached)

    try:
        unit = "celsius" if celsius else "fahrenheit"
        resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,sunrise,sunset,daylight_duration,moonrise,moonset,moon_phase",
                "temperature_unit": unit,
                "precipitation_unit": "mm",
                "wind_speed_unit": "kmh",
                "timezone": "auto",
                "forecast_days": 4,
            },
            timeout=5,
        )
        resp.raise_for_status()
        payload = resp.json()
        current = payload["current"]
        daily = payload["daily"]

        forecast = [
            {
                "date": daily["time"][i],
                "condition_code": daily["weather_code"][i],
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "precipitation_probability": daily["precipitation_probability_max"][i],
                "precipitation_sum": daily["precipitation_sum"][i],
            }
            for i in range(0, min(4, len(daily["time"])))
        ]

        result = {
            "available": True,
            "latitude": lat,
            "longitude": lon,
            "temperature": current["temperature_2m"],
            "apparent_temperature": current["apparent_temperature"],
            "precipitation": current["precipitation"],
            "wind_speed": current["wind_speed_10m"],
            "condition_code": current["weather_code"],
            "unit_celsius": celsius,
            "forecast": forecast,
            "sunrise": daily["sunrise"][0],
            "sunset": daily["sunset"][0],
            "daylight_duration_seconds": daily["daylight_duration"][0],
            "moonrise": daily["moonrise"][0],
            "moonset": daily["moonset"][0],
            "moon_phase_fraction": daily["moon_phase"][0],
        }
        _cache["data"] = result
        _cache["expires_at"] = now + _CACHE_SECONDS
        return weather_location.annotate(result)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return {**_EMPTY, "unit_celsius": celsius}
