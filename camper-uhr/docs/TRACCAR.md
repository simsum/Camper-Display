# Traccar · aktueller lokaler Stand

Neuester Gesamtstand: **0.6.5**. Ankunftswartezeit in Sekunden und Testort aus
GPS-Simulation, siehe `ARRIVAL_MODE.md`. Traccar-Verbindung unverändert.

Neuester Gesamtstand: **0.6.4**, aufgeräumte Einstellungsseite und feste
1480x320-Auflösung; Details in `SETTINGS.md`. Traccar-Verbindung unverändert.

Aktuell auf dem Pi: **0.6.3** (11.09.2026). Nutzer bestätigte nach 0.6.2:
alle Uhren und Traccar funktionieren. Anschließend auf Wunsch die Module
„Strecke“ (`trip`) und „News“ (`news`) entfernt: aus Defaults, gespeicherter
Modulliste, Einstellungen, Factories und Skripteinbindung. Alte Einstellungen
werden gefiltert; auch eine alte offene Einstellungsseite kann die IDs nicht
wieder hinzufügen. Gemeinsame GPS-/Distanzdaten und Traccar bleiben erhalten.
70 Python-Tests auf Pi erfolgreich, Node-App-/Fahrtmodultests erfolgreich.
Vergleich nach Installation bestätigt: alle sonstigen Einstellungen, Aktivierungen,
Laufzeiten und Reihenfolge unverändert. Kiosk gezielt neu gestartet, kein Reboot.
Sicherung: `private Sicherung auf dem Pi; vertraulicher Pfad hier nicht veröffentlicht`; entfernte Moduldateien
dort zusätzlich als `retired-trip.js` und `retired-news.js` wiederherstellbar.

Einrichtung: http://127.0.0.1:8767/ . Vorschau: http://127.0.0.1:8767/journey .
Start: `python scripts/traccar_setup_server.py` (Python-Standardbibliothek).
Der Dienst benötigt Heimnetzzugriff, bindet ausschließlich an 127.0.0.1.
Traccar-Server und VPN bleiben unverändert. Pi-Deploymentstand siehe unten.
Die Fahrtansicht ist seit Version 0.6.1 als eigenes Kiosk-Modul eingebunden.

## Hintergrunddienst

`traccar_cache.py`: ein Worker bereitet beim Dienststart und alle fünf Minuten
den letzten Fahrtag, heute und einen lokal verfügbaren aktuellen Urlaub vor.
Zusätzlich bleiben zuletzt angefragte Zeiträume warm (maximal acht Ergebnisse).
Läuft unabhängig von offener Webseite/aktivem Modul. Kein OS-Zeitplan angelegt:
beim Beenden des lokalen Prozesses endet auch der Hintergrundabruf.

POST `/api/traccar/journey` antwortet sofort mit einem lokalen Snapshot:
`state`, `ready`, `loading`, `version`, `data`, `message`. Keine Traccar-Abfrage
im HTTP-Request. Identische laufende Jobs werden zusammengefasst. UI liest alle
zwei Sekunden den lokalen Stand; nur eine neue Version rendert die Karte erneut.
Während regulärer Aktualisierung bleibt das fertige Ergebnis sichtbar. Fehler
machen `ready=false`; Kiosk darf dieses Modul dann überspringen. Erstbefüllung
kann noch warten: kein erfundener Inhalt. Erneuter Versuch nach Fehler frühestens
nach 60 Sekunden. Bei Kontowechsel werden Cache und alte In-flight-Ergebnisse
verworfen. Manueller Refresh begrenzt auf mindestens zehn Sekunden Abstand.

## Letzter Fahrtag und Kennzahlen

„Letzter Fahrtag · 24 h“: die 24 Stunden bis zur letzten anhand der GPS-Punkte
erkannten Ankunft, NICHT nur der letzte Traccar-Trip und NICHT jetzt minus 24 h.
Die Suche erfolgt tageweise bis 30 Tage zurück. Hinweg, Aufenthalt und Rückweg
innerhalb des Fensters gehören zusammen. Während einer laufenden Fahrt ist der
letzte erfasste Bewegungspunkt das vorläufige Ende. Heute nutzt die lokale
Zeitzone des Backends; Urlaub akzeptiert ISO-Zeitgrenzen, maximal 93 Tage.

Die serverseitigen Tripberichte zählten beim echten Beispiel stündliche
Stillstandsmeldungen zur Fahrzeit. `traccar_motion.py` wertet darum kompakte
Originalpositionen aus: Stillstand unter 3 km/h, maximal 100m Ortsabweichung,
Pause mindestens drei Minuten. Stündliche Null-Geschwindigkeitsmeldungen am
gleichen Ort können eine geschätzte Pause belegen (maximal drei Stunden Abstand).
Anfangs-/Endparken außerhalb der Bewegungsspanne wird nicht als Pause gezählt.
Andere Datenlücken über fünf Minuten sind unbekannt, weder Fahr- noch Pausenzeit;
auch die Karte verbindet diese Lücken nicht. Schätzungen/GPS-Lücken sind sichtbar
im Display markiert. Kein Eingriff in Traccar-Konfiguration oder Tracker.

Strecke nutzt positive, plausible Differenzen von Traccars `totalDistance` vor
Grafikvereinfachung. Fehlen Zähler, werden beobachtete Bewegungspunkte geometrisch
ausgewertet und als Schätzung markiert. Nicht belegte Strecken fehlen ausdrücklich.
Die Durchschnittsgeschwindigkeit wurde auf Nutzerwunsch vollständig aus der
Anzeige entfernt. Fahrtenzahl entspricht durch bestätigte Pausen getrennten Bewegungen.

## Große Routen und Speicher

`traccar_route_data.py` liest `/positions` tageweise, nicht langsame Trip-/Stopp-
Berichte. Tagescache nur im RAM: höchstens 40 Tage/150.000 kompakte Punkte,
aktueller Tag fünf Minuten, vergangene Tage 30 Minuten. Rohantwort höchstens
32 MB; zu große Zeitabschnitte werden halbiert. 15s Socket-Timeout pro Abruf,
120s Arbeitsbudget zwischen Abrufen. Kein Speichern von Fahrdaten auf SD/Disk.

Originaldatensätze werden sofort auf Zeit, Koordinaten, Geschwindigkeit und
Distanzzähler reduziert. Die Anzeige erhält höchstens 1.200 Geometriepunkte:
Heap-basierte Flächenvereinfachung O(n log n), Segment-Endpunkte erhalten.
Kennzahlen werden vorher aus allen Punkten berechnet. Getestet mit 20.000 Punkten.

## Sicherheit und Schnittstellen

Separate Datenbank für Zugangsdaten, nicht Teil allgemeiner Settings/Kioskstatus.
PC: `../.camper-private/traccar-local/traccar-private.db`, außerhalb des statischen
Vorschau-Verzeichnisses. Produktion: CAMPERDISPLAY_DATA_DIR/traccar-private.db.
SQLite-Transaktion, synchronous FULL, POSIX 0600; Windows erbt Benutzerordnerrechte.
Token liegt unverschlüsselt auf dem Datenträger, nie in Browser-Storage, URLs,
Logs oder Antworten. Zugangsdaten niemals in öffentliche Archive aufnehmen.

GET/PUT `/api/traccar/settings` liefert nur API-Adresse, Fahrzeug-ID, token_saved.
Leerer Token behält alten nur bei gleicher API-Adresse. Serverwechsel benötigt
erneute Eingabe. Browser schreibt nur Same-Origin-JSON, lokaler Server prüft Host
und Origin und liefert keine Verzeichnislisten. Kein Ersatz für Authentifizierung
der vorhandenen LAN-Einstellungsseite. Nur im vertrauenswürdigen LAN/VPN verwenden.

POST `/api/traccar/test` prüft `/devices` und aktuelle `/positions`, speichert nichts.
Kontorechte werden nicht verifiziert; in Traccar weiterhin Admin aus/Read-only an.
GET `/api/traccar/vacations` liefert nur Namen und Daten aus Einstellungen und
passendem bestehenden Kalendercache (SHA256-Quellschlüssel); kein Kalenderabruf.
Alle Upstream-Aufrufe sind GET mit Bearer-Header; keine Weiterleitungen, Umgebungs-
Proxys oder TLS-Ausnahmen. Token nicht über `/session?token=...` versenden.
Traccar 6.14.5 `/session` ohne Cookie liefert 404 trotz gültigem Bearer-Token.

## Karte und Verifikation

Leaflet 1.9.4, normale Browser-Kacheln von tile.openstreetmap.org mit HTTP-Cache
und sichtbarer OSM-Attribution. Kein Vorab-/Massendownload von Kartenausschnitten;
OSM sieht den betrachteten Ausschnitt. Erstes Laden des Kartenhintergrunds kann
trotz vorbereiteter Route noch dauern. Format 1480x320, 70% Karte / 30% Zahlen.

21 Python-Tests: Wiederverwendung, Fehler, Kontowechsel während Abruf, 24-h-Grenzen,
90-Minuten-Pause mit wenigen Punkten, unbekannte Lücken, 20.000-Punkte-Reduktion.
JS-Syntax und Python-Kompilierung geprüft. Echter Hintergrundsnapshot am 11.09.2026:
2 Fahrten, ca. 24,9km, 1702s bekannte Fahrzeit, 7201s geschätzte Pause, 1489s unbekannt.
397 Quellpunkte, 394 dargestellte Punkte. Direkter Erstabruf ca. 0,8s auf dem PC;
vorbereitete Antworten beim Wechsel Heute/Letzter Fahrtag ca. 20–30ms.
Browserwechsel und Route/Marker visuell geprüft. Pi-Leistung noch nicht geprüft.

## Übergabestand für die spätere Pi-Übertragung · 11.09.2026

Vom Nutzer bestätigte Vorschau: Durchschnittsgeschwindigkeit vollständig entfernt;
über der Karte nur der Zeitraum der erkannten Fahrten, ohne „CamperVan · Unsere
Fahrt“ und ohne zusätzliche Zeitraum-Überschrift. Strecke, Fahrzeit, geschätzte
Pausenzeit, Stopps und Datenlückenhinweis bleiben erhalten.

Echter Test 03.09. bis einschließlich 06.09.2026 (Europe/Berlin):
API-Grenzen 2026-09-02T22:00:00Z bis 2026-09-06T22:00:00Z.
7.833 Quellpunkte auf 1.200 Kartenpunkte reduziert, nach rund 2 Sekunden bereit
(Messung mit Pollintervall 2 Sekunden); fertige lokale Antworten 4–25ms.
Ergebnis: 677,5km, 36.745s bekannte Fahrzeit, 28.185s geschätzte Pause,
104.288s unbekannte Zeit, 5 Stopps. Strecke wegen GPS-Lücken unvollständig.
Reproduzierbarer Test: `python scripts/check_traccar_period.py` bei laufendem
lokalen Einrichtungsserver. Dies sind PC-Messungen, kein Pi-Leistungsnachweis.

Ursprüngliche Checkliste vor der inzwischen beauftragten Übertragung:

- Pi-Erreichbarkeit und installierten Stand prüfen, bestehende Konfiguration
  sichern und einen Rückweg zur vorherigen Version vorbereiten.
- Fahrtansicht in die tatsächliche Kiosk-Modulfolge und deren Einstellungen
  integrieren; bislang ist sie eine separate lokale Vorschau.
- Traccar-Zugang auf dem Pi separat einrichten/geschützt übertragen; Token nie
  in Quellcode, allgemeine Konfiguration, Protokolle oder öffentliche Archive.
- API-Adresse bleibt einstellbar, VPN unverändert. Vorhandene GPS-Quelle nicht
  ungefragt ersetzen. Hintergrunddienst und Überspringen bei fehlenden Daten prüfen.
- Reale Anzeige, Modulwechsel, Speicher/CPU, Neustart und Fehlerfälle am Pi testen;
  bestehende Display-/Touch-Drehung und Nachtmodus erhalten. Keine automatischen
  Updates oder riskanten Systemänderungen ohne Rückfrage.

Weitere lokale Funktionsstände: `CLOCK_MODULES.md`, `NIXIE_ALIGNMENT.md`,
`NIGHT_MODE.md`, `ARRIVAL_MODE.md` und `PFLICHTENHEFT.md`. Vor Deployment deren
Stand mit dem tatsächlichen Pi abgleichen; nicht voraussetzen, dass alle lokalen
Funktionen schon installiert sind. In diesem Arbeitsschritt wurde nichts auf den
Pi übertragen. Diese Aussage beschreibt den damaligen Vorschau-Arbeitsschritt;
der folgende Abschnitt dokumentiert die spätere Installation.

## Auf dem Pi installiert · 11.09.2026 · Version 0.6.1

Nachtrag 0.6.2: Nutzer meldete fehlende Uhren/Traccar trotz Aktivierung.
API bestätigte alle sieben Uhren und journey in beiden Profilen aktiv, Standmodus,
Display an. Tatsächlicher Kioskstarter nutzte noch `kiosk_build=0.5.1` (beim
ersten Deployment nicht aktualisiert); veralteter HTML-Einstieg als Ursache
vermutet. Starter mit geprüft ausschließlich geändertem Buildwert auf 0.6.2
gebracht. `/`, `/index.html` und `/settings` liefern nun `Cache-Control: no-store`.
Backend und getty@tty1 neu gestartet, kein Pi-Reboot. Health 0.6.2/ok, tatsächliche
Chromium-Startadresse mit 0.6.2, no-store-Header und Linksrotation bestätigt.
Sicherung der beiden geänderten Dateien: `private Sicherung auf dem Pi; vertraulicher Pfad hier nicht veröffentlicht`.
Keine Änderung der vom Nutzer aktivierten Module oder Anzeigedauern.
Physische Bestätigung, dass die fehlenden Module jetzt erscheinen, steht aus.

Ziel: [Pi-Host], `<Pi-Projektpfad>`, Backend-Port 8080.
Sicherung vor Installation: `private Sicherung auf dem Pi; vertraulicher Pfad hier nicht veröffentlicht`.
Enthält alten Anwendungscode (ohne unveränderte venv), konsistente SQLite-Kopien
und privaten Einstellungsvergleich; Verzeichnis nur für root zugänglich.
Bereitstellungsverzeichnis: `<Pi-Projektpfad>`.

69 Python-Tests erfolgreich in separatem Verzeichnis mit der vorhandenen Pi-venv;
alle lokalen Node-Tests erfolgreich, einschließlich Kiosk-Fahrtmodul-Lebenszyklus.
Kein Paketupdate, keine Änderung an VPN, GPS, Boot- oder systemd-Konfiguration.
Backend und bestehende DietPi-getty@tty1-Kiosk-Sitzung gezielt neu gestartet;
kein kompletter Pi-Neustart. Health meldet 0.6.1/ok, Chromium läuft.
Xrandr nach Neustart: 1480x320, HDMI-1 weiterhin `left`.

Alle vorherigen Einstellungen entsprechen exakt der erwarteten Migration
(inklusive Kalenderzugang und Urlauben); danach ausschließlich das neue Modul
`journey` für Stand aktiviert. Zusätzliche Uhren sind in Einstellungen auswählbar,
bleiben bei vorhandenen Konfigurationen zunächst deaktiviert. Nachtmodus-Code
installiert, bisheriges Nachtverhalten bleibt erhalten. Hardware-Backlight fehlt
unter /sys/class/backlight; daher unverändert Software-Abdunklung.

Traccar-Zugang separat per SSH übertragen, private Datenbank mit Modus 0600.
`journey` zeigt den letzten Fahrtag inklusive rückblickender 24 Stunden. Auswahl
Heute/Urlaub bleibt auf `/journey` verfügbar, nicht als zusätzlicher Kioskmodus.
Eingebetteter Renderer nutzt denselben freigegebenen Code, meldet Bereitschaft
an den Elternrahmen (Origin/Source geprüft), überspringt fehlende/fehlerhafte
Daten und rendert Kartenänderungen nur bei aktivem Modul. Lokale Snapshot-Abfrage
alle fünf Sekunden; Traccar-Abfrage weiterhin im Backend-Hintergrunddienst.
Touch fällt an das Hauptfenster durch. Bei Neuaufbau werden Listener entfernt.

Echter Pi-Test: letzter Fahrtag 397 Punkte/24,9km sofort bereit, Snapshot 35–44ms.
03.–06.09.2026: 7.833 Punkte nach etwa 6,36s bereit (2s Pollintervall), 1.200
Kartenpunkte, fertiger Snapshot etwa 67ms. Kennzahlen/GPS-Lücken wie PC-Test.
Speicher-Stichprobe nach Test: 554MiB verfügbar, kein Swap belegt. Das ist kein
Dauerlasttest sämtlicher Uhrenanimationen.
Die direkt vom Pi gelieferte Haupt-Kioskseite wurde im PC-Browser visuell mit
eingebettetem Fahrtmodul geprüft. Physische Sichtprüfung, Touch/Nacht-Umschaltung
und Langzeit-Flüssigkeit durch den Nutzer stehen noch aus.

Wiederherstellung bei Bedarf: Dienst stoppen, Code aus dem gesicherten `app`
zurückkopieren; falls nötig Einstellungen per SQLite-Backup-Verfahren aus der
gesicherten Datenbank wiederherstellen (WAL beachten). Neue private Traccar-DB
nicht in öffentliche Archive aufnehmen. Dienst/Kiosk gezielt neu starten und
Health sowie Einstellungen prüfen. Keine Wiederherstellung automatisch ausführen.
