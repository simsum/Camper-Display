# Camper-Display – Installation und Entwicklung

Zielgerät: Raspberry Pi 3 mit DietPi und 1480 × 320 Pixeln.
Lokale Entwicklung: Python 3.12, Node.js 20 oder neuer für JavaScript-Tests.

## Windows

Im geklonten Projektordner in den Unterordner `camper-uhr/` wechseln:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local.lock.txt
.\.venv\Scripts\python.exe scripts/run_local.py
```

## Linux / macOS (lokale Vorschau)

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/run_local.py
```

Anzeige: http://127.0.0.1:8080/ · Einstellungen: http://127.0.0.1:8080/settings
· Fotos: http://127.0.0.1:8080/photos. Stoppen mit Strg+C.
Ein anderer Port ist mit `--port 8081` möglich.

Der Starter bindet nur an Loopback, verwendet separate Daten in `.local/data/`
und simuliert Displayhardware. GPS-Routerabruf und Linux-Touchleser sind deaktiviert.
Beim ersten Start ist der Nachtzeitplan ausgeschaltet. gpsd hat keinen
voreingestellten Router; trage dessen Adresse unter Einstellungen > GPS ein.
Kalender und Traccar müssen separat eingerichtet werden. Wetter, Karten,
Geocoding und Ankunftsdaten
benötigen Internet. Es werden keine privaten Daten aus einem Git-Klon übernommen.

## Tests

```powershell
.\.venv\Scripts\python.exe scripts/test_local.py
```

Auf Linux/macOS entsprechend `.venv/bin/python scripts/test_local.py`.
Falls Node.js nicht im PATH liegt, `--node <Pfad-zu-node>` ergänzen.
Der Starter nutzt temporäre Daten und prüft Python-Pakete, Python-/JavaScript-Tests
und die Syntax der Frontend-JavaScript-Dateien. Diese Tests ersetzen keinen
Hardwaretest am Raspberry Pi.

## Vorschauen und Screenshots

`/public-preview.html` zeigt die Produktionsrenderer mit festen Beispieldaten.
Die Auswahl erfolgt über `?screen=panorama`, `led`, `flip`, `weather`, `sun`,
`calendar` oder `photos`. Die Seite verändert keine Einstellungen und fragt
keine privaten APIs ab. Die Screenshot-Galerie steht in `docs/screenshots/`.

Weitere Vorschauen: `/map-preview.html`, `/journey-preview.html`,
`/weather-preview.html`, `/photo-preview.html`. Karten können Internet abrufen.

## Pi-Betrieb und Lizenzen

Die [DietPi-Anleitung](deploy/DIETPI.md) beschreibt eine manuelle Installation.
Eine neue virtuelle Umgebung ist auf jedem Zielgerät erforderlich.
Keine automatische Übertragung von Entwicklungsdaten auf ein vorhandenes Gerät.
Siehe [Arbeitsstand](../UEBERGABE.md), [Sicherheit](../SECURITY.md) und
[Lizenzen/Quellen](../THIRD_PARTY_NOTICES.md).
