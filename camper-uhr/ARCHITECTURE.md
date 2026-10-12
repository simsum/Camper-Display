# Camper-Display – Grundarchitektur

## Laufzeit

- `backend/`: FastAPI stellt die lokale API und die statischen Frontend-Dateien bereit.
- `frontend/`: feste 1480×320-Designfläche; einzelne Anzeigen liegen in `js/screens/`.
- `deploy/`: systemd-Dienst und DietPi-Kiosk-Startskript.
- `/var/lib/camperdisplay/`: einzige dauerhaft veränderliche Anwendungsablage auf dem Pi.

## Modulvertrag

Ein Frontend-Modul exportiert eine Factory `create<Name>Screen(settings)`. Sie liefert:

```text
element   – Wurzelelement mit Klasse "screen"
onMount() – nach dem Einfügen und beim Aktivieren
onTick(status, settings) – Aktualisierung aus dem gemeinsamen Status
```

Die Registry in `frontend/js/app.js` entkoppelt die Module. Fehler in einem Modul werden abgefangen, damit Uhr und übrige Anzeigen weiterlaufen. `news` und `calendar` sind bereits registriert, standardmäßig aber deaktiviert.
Das Datums-/Urlaubsmodul ist inzwischen standardmäßig im Stand aktiviert; News bleibt ein nicht verfügbares Platzhaltermodul.

`backend/operating_state.py` bildet aus der gemeinsamen GPS-Schnittstelle den Zustand `stand` oder `drive`. Das Frontend verwendet dieselbe Modulreihenfolge und liest daraus je Zustand Aktivierung, Dauer und Helligkeit. Testzustände überschreiben nur die Ausgabe der Zustandsmaschine und verändern keine GPS-Daten. `frontend/js/screens/calendar.js` berechnet Urlaubs- und Jahresfortschritt ausschließlich aus lokaler Zeit und den dauerhaft gespeicherten Urlaubszeiträumen; es benötigt keine Netzverbindung.

## Daten und Stromausfall

`backend/calendar_client.py` lädt einen optionalen öffentlichen iCloud-Feed in einem eigenen Hintergrundthread alle 15 Minuten. `calendar_url.py` begrenzt URLs und Weiterleitungen auf HTTPS-iCloud-Freigabelinks. Die Parser `icalendar` und `recurring-ical-events` behandeln Zeitzonen und wiederkehrende Termine. Kalender-URLs werden nicht im Status oder in Fehlermeldungen ausgegeben. Das Statusfeld `calendar` enthält importierte Reisen, Abrufzustand und letzten Erfolgszeitpunkt; die Web-Konfiguration verwendet zusätzlich `/api/calendar/status` und `/api/calendar/refresh`. Importierte und manuelle Urlaube werden erst im Frontend zusammengeführt, sodass Kalenderlöschungen keine manuellen Einträge verändern. Der Quellhash verhindert, dass ein anderer Kalender den alten Offline-Stand übernimmt. Der Cache liegt als eigener Datensatz in derselben SQLite-Datenbank.

Einstellungen liegen in SQLite. WAL, `synchronous=FULL`, begrenzte WAL-Größe und ein Schreib-Lock-Timeout schützen einzelne Transaktionen. GPS-Positionen und Fahrspur bleiben absichtlich nur im RAM. Der Dienst wird nach Abstürzen automatisch neu gestartet; der Kiosk wartet beim Boot auf `/api/health`.

Ein schreibgeschütztes Root-Dateisystem ist absichtlich nicht Teil der automatischen Installation: Das greift tief in DietPi ein und sollte erst nach einem eigenen Backup und einem geplanten Neustart aktiviert werden.

## Spätere Datenquellen

- Uhr-Themes: lokale Assets unter `frontend/assets/nixie-themes/`
- Wetter: `backend/weather_client.py`, mit Cache und leerem Offline-Zustand
- Himmel: Sonnen- und Monddaten aus derselben zweistündig gültigen Standortabfrage; ohne aktuelle Daten wird das Modul übersprungen
- Karte: `frontend/js/screens/map.js`, GPS bleibt auch ohne Kartenbibliothek aktiv
- News: späterer Backend-Cache plus `frontend/js/screens/news.js`
- Datum/Urlaub: persistente Liste in den gemeinsamen Einstellungen plus `frontend/js/screens/calendar.js`; astronomische Jahreszeitengrenzen werden lokal berechnet
