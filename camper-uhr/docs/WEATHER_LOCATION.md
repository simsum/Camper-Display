# Wetterstandort · auf Pi installiert am 18.09.2026

Statt „Camper-Standort“ zeigt das Wettermodul den Ort des tatsächlichen
Wetterabrufs. Anfragekoordinaten liegen im Wettercache und werden als latitude
und longitude mitgeliefert. Der Name wird ausschließlich für diese Koordinaten
ermittelt, niemals aus der inzwischen aktuellen Fahrzeugposition übernommen.
Der bestehende zweistündige Wettercache bleibt unverändert: auch während einer
Fahrt bezeichnet der Name genau den noch angezeigten Wetterstand.

weather_location.py löst Gemeinde/Ort und Land über Nominatim auf. Ein einzelner
Hintergrundworker, maximal acht RAM-Einträge, Namenscache 24 Stunden,
Fehlercache zehn Minuten. Gemeinsamer HTTP-Client mit der Ankunftsanzeige:
identifizierender User-Agent, HTTPS-Hostbeschränkung, Antwortlimit und global
mindestens 1,1 Sekunden Abstand zwischen Nominatim-Anfragen. Kein zusätzlicher
Netzwerkabruf im Statusrequest. Wetter-Anfragekoordinaten werden dafür an
Nominatim/OpenStreetMap übermittelt; kein Schreiben auf die SD-Karte.

Bis zur Auflösung oder bei Fehlern erscheinen die Wetter-Anfragekoordinaten,
auf drei Nachkommastellen gerundet. Fehlen auch diese: „Wetterstandort unbekannt“.
Ortsname über textContent, lange Namen mit Ellipse und vollständigem Tooltip,
sichtbarer OpenStreetMap-Quellenlink. Keine Straße oder Hausnummer angefordert.

88 Python-Tests auf PC/Pi bestanden, lokale JS-Tests ebenfalls. Browser-Vorschau
mit ausdrücklich fiktiven Bamberg-Wetterwerten geprüft. Laufender Pi bestätigt:
Wetter verfügbar, Anfragekoordinaten vorhanden und Ortsname erfolgreich aufgelöst;
der private Standort wurde nicht in Diagnoseausgaben ausgegeben.

Sicherung: private Sicherung auf dem Pi; vertraulicher Pfad hier nicht veröffentlicht.
Sechs Anwendungsdateien installiert, Prüfsummen und Health kontrolliert,
Einstellungen exakt unverändert. Backend/Kiosk neu gestartet, kein Pi-Reboot.
Wetter-/CSS-Cachekennung: 0.6.6-place1; API-Releasekennung weiterhin 0.6.5.
Staging: <Pi-Projektpfad>.
