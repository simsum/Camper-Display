# Lizenzen und Quellen

## Projektcode und eigene Gestaltung

Copyright (C) 2026 Sven Steinmeier und Mitwirkende.
Der eigene Quellcode und die zugehörige Projektdokumentation werden unter der
GNU General Public License, Version 3 (SPDX: **GPL-3.0-only**) bereitgestellt.
Der vollständige Text steht in [LICENSE](LICENSE). Es besteht keine Garantie;
die entsprechenden Bestimmungen der GPLv3 gelten.

Nach Auskunft des Projektinhabers stammen die Landschaftshintergründe,
Foto-Demomotive und Uhr-Zifferngrafiken aus eigenen KI-Generierungen bzw.
eigenen Entwürfen. Soweit Rechte daran bestehen, werden diese eigenen Assets
ebenfalls unter GPL-3.0-only bereitgestellt. Das umfasst die Verzeichnisse
`frontend/assets/calendar`, `nixie-themes`, `photo-demo`, `sky` und `weather`
unter `camper-uhr/` sowie daraus erstellte Vorschauen.

Die folgenden Fremdmaterialien behalten ihre jeweiligen Lizenzen.

## Wikimedia-Beispielfoto und Wikipedia-Text

- Datei: `camper-uhr/previews/anfo-photo.jpg`.
- Urheberhinweis: **© Superbass / CC BY-SA 4.0 (via Wikimedia Commons)**.
- Original und Beschreibung: [2018-08-17-Anfo-0435.jpg](https://commons.wikimedia.org/wiki/File:2018-08-17-Anfo-0435.jpg).
- Lizenz: [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- Bearbeitung: verkleinerte JPEG-Vorschau; die Anzeige kann einen Bildausschnitt verwenden.
- Der gekürzte Artikeltext in `camper-uhr/previews/anfo-fixture.js` stammt aus
  [Wikipedia: Anfo](https://de.wikipedia.org/wiki/Anfo) und steht unter CC BY-SA 4.0.
  Die verlinkte Versionsgeschichte nennt die Mitwirkenden. Abrufstand der
  bestehenden Testdatei: September 2026; sie ist keine aktuelle Ortsauskunft.

Diese Hinweise gelten auch für Screenshots, die das Foto oder den Artikel zeigen.
Die allgemeine Projektlizenz ersetzt die Lizenzen dieser Inhalte nicht.

## Software-Abhängigkeiten

Die Bibliotheken werden über Python-Pakete oder zur Laufzeit aus einem CDN
bezogen; sie sind nicht als Bibliotheksquellcode in diesem Repository enthalten.
Ihre eigenen Lizenz- und Copyright-Hinweise bleiben maßgeblich, auch für
transitive Abhängigkeiten. Beim Weitergeben einer gebündelten Installation sind
die entsprechenden Lizenztexte und gegebenenfalls Quellcodepflichten zu beachten.

| Direkte Abhängigkeit | Lizenz laut Paket/Projekt |
| --- | --- |
| FastAPI | MIT |
| Uvicorn | BSD-3-Clause |
| gps3 | MIT |
| HTTPX | BSD-3-Clause |
| icalendar | BSD-2-Clause |
| recurring-ical-events | LGPL-3.0-or-later |
| python-qrcode | BSD; Lizenztext im Python-Paket |
| Leaflet | BSD-2-Clause |
| MapLibre GL JS | BSD-3-Clause |

## Externe Daten

Karten und Ortsnamen verwenden OpenStreetMap; siehe
[Copyright und Datenlizenz](https://www.openstreetmap.org/copyright).
Wetter- und Himmelsdaten verwenden [Open-Meteo](https://open-meteo.com/).
Wikipedia/Wikimedia-Inhalte werden mit den jeweiligen Quellen- und
Lizenzhinweisen angezeigt. Die Nutzungsbedingungen der Dienste gelten unabhängig
von der Projektlizenz. Die Anwendung ist kein Offline-Kartenpaket.
