# Ankunftsanzeige – auf dem Pi installiert

## Aktueller Stand 0.6.5 · 11.09.2026

Nutzer hat die Anfo-Testanzeige auf dem physischen Pi-Display bestätigt.
Die nachfolgende ältere Beschreibung dokumentiert den ursprünglichen Aufbau;
für Wartezeit und Testort gelten jetzt diese Änderungen:

- Ankunftswartezeit durchgehend in **Sekunden**: `arrival_wait_seconds`, Standard
  300, Bereich 1–3600. Alte Minutenwerte werden beim Laden exakt mit 60 multipliziert;
  bei gleichzeitig vorhandenem Sekundenwert hat dieser Vorrang. Kein Zurücksetzen.
  Die Umschaltung in den Standmodus bleibt zusätzliche Voraussetzung.
- „Ankunft mit Simulationsort testen“ übernimmt das aktuelle Feld „Ort“ unter
  GPS-Simulation. Die Simulation muss nicht laufen. Kein festes Anfo mehr.
  POST `/api/arrival/test` verlangt JSON `{ "place_name": "Bamberg" }` mit einem
  nichtleeren, getrimmten Namen (maximal 120 Zeichen). Leere Eingaben werden auch
  serverseitig abgewiesen. Der übergebene Ort wird beim Start festgehalten.
- Gemeinsamer Geocoder wie GPS-Simulation, aber Ortsauflösung und Wikipedia-Abruf
  laufen im Ankunfts-Hintergrundthread. Keine Änderung von GPS-Fix, Geschwindigkeit,
  Höhe oder Fahrtmodus. Test nutzt die Höhe des ermittelten Orts, nicht eine
  möglicherweise abweichende GPS-/Simulationshöhe. Nacht-/Fahrt-/Displaypriorität
  und Testbegrenzung bleiben erhalten. Unbekannter Ort/fehlende Verbindung führt
  zu einer Meldung statt zur Anzeige eines Ersatz-Testorts.

75 Python-Tests auf Pi erfolgreich, einschließlich genauer Sekunden-Schwelle,
Altwertmigration, API-Eingabemodell, Übernahme des Orts, Fehlerfall und Nachweis,
dass der Worker keinen simulierten GPS-Fix setzt. Browserprüfung in isolierter
Testumgebung: leeres Ortsfeld abgefangen, „Bamberg“ im Request bestätigt.
Installiert mit Backend-Neustart, kein Pi-/Kiosk-Neustart. Wartezeit bei dieser
Installation von 5 Minuten auf 300 Sekunden umgerechnet; exakter Vergleich
bestätigt alle übrigen Einstellungen unverändert.
Sicherung: `private Sicherung auf dem Pi; vertraulicher Pfad hier nicht veröffentlicht`.

## Ursprüngliche Umsetzung (historisch)

## Bedienung

Unter Einstellungen → Ankunftsanzeige: Aktivierung, „Angekommen nach“ (1–60 Minuten, Standard 5), „Ankunft anzeigen für“ (5–180 Sekunden, Standard 30), Testschaltfläche für Anfo/Italien. Neue Werte vor dem Test speichern. Kein zusätzliches dauerhaft rotierendes Modul: die Begrüßung unterbricht die normale Folge einmal und setzt sie am bisherigen Modul fort. Touch beendet die Begrüßung vorzeitig.

Eine bestätigte Fahrt mit gültigem GPS aktiviert die Erkennung. Der Stillstand zählt ab Unterschreiten der vorhandenen Stand-Geschwindigkeit; Bewegung oder GPS-Ausfall setzt die Wartezeit zurück. Anzeige frühestens nach dem vorhandenen Wechsel in den Standmodus und nach der eingestellten Ankunftswartezeit (nicht beide Zeiten addiert). Ein langer Stau bleibt ohne weitere Sensorsignale grundsätzlich nicht sicher von Ankunft unterscheidbar. Beim Booten im Stand keine Begrüßung. Eine neue Fahrt aktiviert die Erkennung erneut.

Nachtfenster (auch während Touch-Aufwecken), manuelles/automatisches Ausschalten und Fahrt haben Vorrang. Unterdrückte Ankünfte werden nicht morgens nachgeholt. Die Anzeige endet bei erneuter Fahrt oder Nachtbeginn. Der Browser beendet die Ankunft auch bei anschließendem Backend-Ausfall lokal zum Ablaufzeitpunkt.

## Datenweg auf dem Pi

`arrival_provider.py` läuft mit Python-Standardbibliothek, ohne KI und ohne zusätzliche Pakete. Nach Ankunft erfolgt einmal eine Nominatim-Rückwärtsabfrage auf Gemeindeebene (zoom 10). GPS-Koordinaten werden dafür an Nominatim/OpenStreetMap sowie für Sonnenuntergang an Open-Meteo übermittelt. Die eindeutig verknüpfte Wikidata-Kennung bestimmt den deutschen Wikipedia-Artikel; alternativ Italienisch/Englisch, ohne automatische Übersetzung. Artikelkennung wird gegengeprüft, keine ungesicherte Namenssuche. Text: höchstens drei Einleitungssätze und 330 Zeichen, für fünf Displayzeilen gekürzt. Einwohnerzahl mit Datenjahr; neuere datierte Zahlen aus dem deutschen Einleitungstext haben Vorrang vor älteren Wikidata-Zahlen. Fläche und Ortshöhe mit überprüfter Einheit; echte GPS-Höhe hat Vorrang und ist so beschriftet. Fehlende Werte werden ausgelassen.

Foto aus dem Wikipedia-Artikel bzw. dessen verknüpftem Wikidata-Foto, nicht per offener Bildsuche. Commons liefert bereits die verkleinerte Vorschau (maximal 1280 px breit, 1600 px hoch, Download maximal 1,5 MB). Kein großer Originaldownload, keine Bildbearbeitung auf dem Pi, keine Animation. Karten, Wappen, Logos und SVG-Dateien werden übersprungen. Erlaubte Fotolizenzen: CC0/Public domain sowie CC BY/CC BY-SA mit vollständigen Metadaten; unbekannte Bedingungen führen zur Anzeige ohne Bild. Kleine sichtbare Quellenzeile mit Fotograf, Lizenz und Ausschnitt-Hinweis, verlinkte Datei-/Lizenzseiten. Wikipedia-Text mit Artikel- und Lizenzlink; OpenStreetMap-Hinweis separat. Fremde Texte werden ausschließlich als Text, nie als HTML eingefügt.

Netzwerkabrufe laufen in einem Hintergrundthread, nicht im Status-Endpunkt. Feste HTTPS-Hostliste auch bei Weiterleitungen, Antwortgrößenlimits und Zeitlimits; Nominatim mit identifizierendem User-Agent und höchstens einer Anfrage pro 1,1 Sekunden. Kein permanentes Polling der Ortsdienste. Nur die letzte Ankunft einschließlich Foto liegt im RAM; Bildroute ist an ihre zufällige Ereigniskennung gebunden. Keine Foto-/Ortsdaten-Schreibvorgänge auf der SD-Karte. Bei Netzausfall bleibt eine einfache Ankunft mit verfügbaren Werten, neutralem Hintergrund und ohne erfundene Ortsangaben. GPS-/Betriebszustand wird nach dem Abruf erneut geprüft, größere Positionssprünge verwerfen die Antwort.

## Anfo-Test

Der Test nutzt den dokumentierten Beispielort; es werden keine persönlichen Koordinaten gespeichert. Die Testschaltfläche benutzt genau den Produktionsprovider, verändert aber weder GPS-Fix noch gespeicherte Einstellungen oder Betriebsmodus. Maximal ein Test pro Minute. Testanzeige respektiert Nachtfenster, Fahrt und Display aus; „TESTORT“ kennzeichnet sie.

Lokaler Live-Test am 11.09.2026: Anfo → Wikidata Q103420 → deutscher Wikipedia-Artikel Anfo. Rückgabe: Lombardei/Italien, Ortshöhe 400 m, 439 Einwohner (2025), 23,83 km², Sonnenuntergang 19:37. Ortsfoto: `2018-08-17-Anfo-0435.jpg`, Superbass, CC BY-SA 4.0. Verkleinertes JPEG 525.425 Bytes; letzter Abruf am PC etwa 1,48 Sekunden (keine Aussage über Pi-Leistung).

Reproduzierbarer Abruf auf PC oder Pi: `python scripts/arrival_probe.py`. Optional `--image-out <Datei>` speichert ausschließlich das heruntergeladene Foto für eine lokale Vorschau. `previews/arrival-anfo.html` zeigt den Produktionsrenderer mit der gespeicherten Live-Antwort vom PC, keinen simulierten Pi-Test. JSON-Daten: `previews/anfo-fixture.js`, Bild: `previews/anfo-photo.jpg`.

Prüfungen: acht Python-Tests für Ereigniserkennung, GPS-/Bewegungsreset, Deaktivierung, Nacht-/Displaypriorität, Wertevalidierung, Netzwerk-/Bildschutz, Offline-/Fehlzuordnungsfall und Testbegrenzung. App-Test prüft Ablauf, pausierte Rotation, Rückkehr, Verwerfen bei Nacht und manuelles Schließen. Browserprüfung für Anfo-Daten, Foto, Attribution, Layout und bildlosen Zustand bestanden. Bestehende Uhr-/Nachtmodus-Tests bleiben separat ausführbar.

Pi [Pi-IP] am 11.09.2026 per SSH geprüft: Timeout. Daher kein Deployment, kein Neustart und keine Änderung seiner GPS-/Systemkonfiguration. Direkter Abruf und Flüssigkeit am Pi sowie kompletter End-to-End-Gerätetest stehen aus.
