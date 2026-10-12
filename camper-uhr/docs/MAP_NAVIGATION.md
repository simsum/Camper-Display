# Navi-Kartenansicht – lokaler Entwicklungsstand 18.09.2026

## Nachtrag: GPS-Beruhigung auf Pi installiert · 18.09.2026

Die normale Karte zeigt keine Ausrichtungsbeschriftung mehr. Testdaten behalten
„SIMULATION“. Reales GPS wird zentral in `gps_client.MotionFilter` gefiltert:
Median aus maximal fünf Messungen der letzten vier Sekunden, mindestens drei
Messungen, Bewegungsbeginn ab 4 km/h nach zwei Sekunden Bestätigung, Rückkehr zu
0 unter 2 km/h. Während Bewegung exponentielle Geschwindigkeitsglättung mit
Zeitkonstante einer Sekunde. Dadurch verzögert sich die Erkennung echter Bewegung
um einige Sekunden zusätzlich zur unveränderten Stand-/Fahrt-Hysterese.

Kurs ab 5 km/h aktualisiert, darunter festgehalten; zirkulärer Medoid aus drei
Kurswerten und Glättung über den kürzesten Winkel (Zeitkonstante 1,2 Sekunden).
Bei Stillstand wird der Filterkurs verworfen; die aktive Fahrtkarte behält bis
zum Standmodus ihre letzte Richtung. Ungültige Geschwindigkeit, Verbindungsverlust
und Messpausen über fünf Sekunden setzen den Filter zurück. Simulation bleibt
ungefiltert, damit eingegebene Testwerte exakt reproduzierbar sind. Keine neuen
persistenten Einstellungen. Der Filter reduziert Rauschen, ersetzt aber keine
weitere Bewegungsquelle bei dauerhaft falschen GPS-Messungen.

83 Python-Tests auf PC und Pi sowie sieben lokale JavaScript-Testsuiten bestanden.
Neue Fälle: Standrauschen, isolierte Spitzen, Anfahren/Anhalten, echte Kurve,
Nordübergang, ungültige/alte Messungen und zeitbasierte Bestätigung bei hoher Rate.
Browser bestätigt entfernte Ausrichtungsbeschriftung.
Vor Installation neue geprüfte Sicherung:
`private Sicherung auf dem Pi; vertraulicher Pfad hier nicht veröffentlicht`.
Vier Anwendungsdateien installiert, Health/Prüfsummen geprüft, Einstellungen exakt
unverändert; nur Backend und Kiosk neu gestartet. Karten-Cachekennung 0.6.6-nav2.

Das Kartenmodul nutzt MapLibre GL JS 5.6.0 mit den bisherigen OpenStreetMap-
Rasterkarten. Während `operating.mode=drive` beträgt die Neigung 45 Grad,
der Fahrzeugmarker liegt unterhalb der Mitte und der GPS-Kurs zeigt nach oben.
Im Stand: Neigung 0, Norden oben, Positionspunkt statt Richtungspfeil.
Die bestehende Stand-/Fahrt-Hysterese bleibt unverändert. Keine Routenplanung
oder Abbiegehinweise, keine Gebäude-/Geländehöhen.

GPSD `TPV.track` wird als optionales `gps.heading_deg` durchgereicht (Grad ab
wahrem Norden). Nur endliche Werte von 0 bis unter 360 bei mindestens 3 km/h
werden übernommen. Kein Kompasskurs aus GPS-Rauschen berechnet. Bei kurzem Halt
im aktiven Fahrtmodul bleibt die letzte Richtung; fehlender Kurs während Bewegung
führt zu Nordausrichtung mit Hinweis. Stand, GPS-Ausfall, Wechsel der GPS-Quelle
und erneuter Modulstart verwerfen die gemerkte Richtung. `mode < 2` und eine
geschlossene GPSD-Verbindung melden Verbindungsverlust statt eines alten Kurses.

Die GPS-Simulation hat ein optionales Feld „Fahrtrichtung“. API:
`POST /api/debug/simulate-position` mit `heading_deg` (0 ≤ Wert < 360).
Die Änderung ist abwärtskompatibel; kein neues persistentes Einstellungsfeld.

MapLibre wird beim Aktivieren nachgeladen. Außerhalb des Moduls werden Karte,
WebGL-Kontext, Listener und laufender Fahrspurabruf freigegeben. Begrenzte
Pixeldichte und Kachelcache, keine dauerhafte Kamerafahrt; Statusänderungen
aktualisieren die Kamera unmittelbar. Bei fehlendem WebGL erfolgt ein Rückfall
auf Leaflet (flach, Norden oben, sichtbar als 2D gekennzeichnet).
Traccar-Fahrtansicht bleibt bei Leaflet. OSM-Quellenhinweis ist sichtbar.
CDN- und Kartenabrufe benötigen Internet; kein Offline-Kartendownload.

## Lokale Prüfung

`http://127.0.0.1:8080/map-preview.html` verwendet den Produktionsrenderer mit
klar gekennzeichneten Bamberg-Testdaten. Schalter: Stand, vier Himmelsrichtungen,
kurzer Halt, GPS-Ausfall. Keine Änderung gespeicherter Einstellungen oder
Backend-GPS-Daten durch diese Vorschau.

Tests: GPS-Kursvalidierung, ungültiger Fix, Simulator und API-Weitergabe;
JavaScript-Kameralogik für Fahrt/Stand, Halt, fehlende Richtung und Quellenwechsel.
Browser: Fahrt nach Ost/West und Stand visuell geprüft. Die eigentliche App nutzt
denselben Kartenrenderer. Testbefehl siehe README.

## Auf dem Pi installiert · 18.09.2026

Pi unter `[Pi-Host]` geprüft. Sicherung:
`private Sicherung auf dem Pi; vertraulicher Pfad hier nicht veröffentlicht`.
129 kopierte Dateien per SHA-256 geprüft; Datenbanken über SQLite-Backup-API
gesichert und mit integrity_check geprüft. Private Sicherung bleibt auf dem Pi.

78 Python-Tests im separaten Staging auf dem Pi bestanden. Ein temporärer
Kiosk-Test mit automatischer Rückkehr zeigte die Navi-Vorschau; Nutzer bestätigte
Karte und Text auf dem physischen Display. Der bisherige GPU-Abschalter wurde
nach ausdrücklicher Freigabe durch `--enable-webgl` ersetzt. Headless-Proben waren
nicht aussagekräftig für den sichtbaren Kiosk; kein WebGL2-Nachweis behauptet.

Anschließend 11 Anwendungs-/Dokumentationsdateien mit Prüfsummenvergleich
installiert, Backend und getty@tty1 gezielt neu gestartet. Kein Pi-Reboot, keine
Paketupdates. Einstellungen vor/nach Installation exakt identisch. Health ok,
1480 × 320 und Linksrotation erhalten. Nutzer bestätigt auch normale Modulfolge.
Speicherstichprobe danach: 473 MiB verfügbar, 9 MiB Swap belegt; kein Dauerlasttest.
Flüssigkeit während echter Fahrt und dauerhaft wechselnder Module weiter beobachten.

API-Releasekennung bleibt 0.6.5 mit Navi-Erweiterung; Kiosk-Build und Kartenassets
tragen `0.6.6-nav1`. Testserver und automatischer Rückkehrtimer sind gestoppt.
Staging: `<Pi-Projektpfad>`.
Bei nötigem Rücksprung stellt dessen `rollback-navigation-test.sh` die geänderten
vorhandenen Anwendungsdateien und den ursprünglichen Kioskstarter aus der Sicherung
wieder her und startet Backend/Kiosk neu. Keine Datenbankwiederherstellung nötig,
da keine Einstellungen migriert oder geändert wurden. Rücksprung nur bei Bedarf.

Referenzen: https://maplibre.org/maplibre-gl-js/docs/examples/set-perspective/
und https://www.gpsd.io/gpsd_json.html (TPV.track).
