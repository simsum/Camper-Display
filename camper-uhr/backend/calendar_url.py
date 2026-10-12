from urllib.parse import urlsplit, urlunsplit


def normalize_calendar_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        host = (parts.hostname or "").lower()
        valid = (
            parts.scheme in ("https", "webcal")
            and host.endswith(".icloud.com")
            and parts.path.startswith("/published/")
            and parts.port in (None, 443)
            and not parts.username and not parts.password
            and not parts.fragment
            and not any(ord(char) < 33 for char in value)
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Bitte den öffentlichen iCloud-Kalenderlink aus 'Link teilen' einfügen.")
    return urlunsplit(("https", host, parts.path, parts.query, ""))
