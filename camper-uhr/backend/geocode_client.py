import httpx

# Preferred countries when a place name matches multiple locations worldwide
# (e.g. "Bamberg" exists in Germany and South Carolina, USA) - the camper
# travels in German-speaking Europe, so bias toward those results.
_PREFERRED_COUNTRIES = ("DE", "AT", "CH", "IT", "FR", "NL", "BE", "DK", "CZ", "PL")


def geocode(name: str) -> tuple[float, float] | None:
    if not name.strip():
        return None
    try:
        resp = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": name, "count": 10, "language": "de"},
            timeout=5,
        )
        resp.raise_for_status()
        results = resp.json().get("results")
        if not results:
            return None

        best = next(
            (r for r in results if r.get("country_code") in _PREFERRED_COUNTRIES),
            results[0],
        )
        return best["latitude"], best["longitude"]
    except (httpx.HTTPError, KeyError, IndexError):
        return None
