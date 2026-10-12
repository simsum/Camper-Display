# Pflichtenheft – Camper-Display

**Dokumentstand:** 1.0
**Datum:** 11.09.2026
**Zielsystem:** Raspberry Pi 3 mit DietPi und Chromium-Kiosk

## 1. Ziel und Produktidee

Das Camper-Display ist eine modulare Animations- und Informationsplattform für den festen Einbau in einen Camper. Eine optisch hochwertige, animierte Uhr bildet die Hauptanwendung. Weitere Informationen werden als eigenständige, nacheinander dargestellte Module ergänzt.

Optik und Animation haben Vorrang vor maximaler Informationsdichte. Neue Ideen sollen später als zusätzliche Module ergänzt werden können, ohne die Kernanwendung umzubauen.

## 2. Zielhardware und Umgebung

### Muss-Anforderungen

- Raspberry Pi 3 als Zielrechner
- DietPi als Betriebssystem
- 11,9-Zoll-HDMI-Touchdisplay
- native Anzeigefläche von 1480 × 320 Pixeln
- Chromium im Kioskmodus ohne vollständige Desktopumgebung
- Bildausgabe um 180 Grad gegenüber der ursprünglichen Einbaulage gedreht, damit die Displayanschlüsse oben liegen
- WaveShare-Touchkoordinaten passend zur gedrehten Einbaulage dauerhaft um 180 Grad transformiert
- lokales Camper-Netzwerk über einen GL.iNet-Mobilfunkrouter
- Internetzugang im Normalfall über die SIM-Karte des Routers
- Position, Geschwindigkeit und Höhe möglichst über GNSS/GPS des Routers
- Bedienung der Konfiguration von Smartphone oder Notebook im lokalen Netzwerk

### Spätere Erweiterungen

- IMU-Sensor für Neigung, Wasserwaage, künstlichen Horizont und G-Kugel
- weitere Camper-Sensoren oder Datenquellen über klar definierte Schnittstellen

## 3. Bedienkonzept

### Touchdisplay

- Ein erster Touch muss ein ausgeschaltetes Display für eine einstellbare Zeit aufwecken, ohne dabei das aktuelle Modul zu wechseln.
- Bei eingeschaltetem Display muss kurzes Tippen zum nächsten aktuell erlaubten Modul wechseln.
- Wischen nach links beziehungsweise rechts muss zum nächsten beziehungsweise vorherigen erlaubten Modul wechseln.
- Deaktivierte Module müssen dabei übersprungen werden.
- Die eigentliche Konfiguration erfolgt nicht auf dem Kioskdisplay.
- Das Kioskdisplay enthält keine Einstellmenüs.

### Weboberfläche

- Die Weboberfläche dient ausschließlich der Konfiguration und Wartung.
- Eine Live-Vorschau ist für das MVP nicht erforderlich.
- Sie muss im lokalen Camper-Netzwerk erreichbar sein.
- Sie ist ohne zusätzliche Anmeldung oder Passwortabfrage erreichbar.
- Das vertrauenswürdige, abgesicherte Camper-WLAN bildet die Zugriffsgrenze.
- Änderungen sollen ohne Neustart der Anwendung übernommen werden, soweit dies technisch sinnvoll ist.

## 4. Betriebszustände und Displaylogik

Das System unterscheidet mindestens folgende Zustände:

| Zustand | Displayverhalten |
|---|---|
| Fahrt | immer eingeschaltet; der Stand-Zeitplan wird ignoriert |
| Stand innerhalb der Aktivzeit | eingeschaltet |
| Stand außerhalb der Aktivzeit | ausgeschaltet bzw. Bildausgabe deaktiviert; Touch bleibt aktiv |
| Manuelles Aufwecken | für eine einstellbare Dauer eingeschaltet |

Für Stand und Fahrt gelten getrennt einstellbare Helligkeitswerte. Beim manuellen Aufwecken wird die Stand-Helligkeit verwendet.

Im MVP gilt an allen Wochentagen dasselbe, über die Weboberfläche einstellbare tägliche Aktivzeitfenster. Unterschiedliche Zeitpläne je Wochentag können später ergänzt werden.

### Standardwerte

- tägliche Aktivzeit im Stand: 08:00 bis 22:00 Uhr
- Helligkeit im Stand: 40 Prozent
- Helligkeit während der Fahrt: 100 Prozent
- manuelle Aufweckdauer außerhalb der Aktivzeit: 120 Sekunden
- jede weitere Berührung während der manuellen Aufweckphase setzt deren Zeitgeber erneut auf 120 Sekunden beziehungsweise auf den konfigurierten Wert

Der Fahrzustand soll aus GPS-Geschwindigkeit mit Schwellwert und Hysterese bestimmt werden. Ein kurzer Halt, beispielsweise an einer Ampel, darf nicht sofort zum Zustand „Stand“ führen.

### Festgelegte Zustandswechsel

- Wechsel zu „Fahrt“, wenn mindestens 8 km/h für 10 Sekunden anliegen.
- Wechsel zurück zu „Stand“, wenn weniger als 3 km/h für 3 Minuten anliegen.
- Bei Ausfall des GPS-Signals wird der letzte erkannte Zustand zunächst 5 Minuten beibehalten.
- Ist nach 5 Minuten weiterhin kein GPS-Signal verfügbar, wechselt das System aus Sicherheitsgründen in den Zustand „Stand“.

## 5. Szenen- und Modulsteuerung

### Muss-Anforderungen

- Aktive Module laufen automatisch in einer festgelegten Reihenfolge durch.
- Für Stand und Fahrt gilt dieselbe gemeinsame Modulreihenfolge.
- Für jedes Modul muss getrennt einstellbar sein, ob es im Stand und während der Fahrt aktiv ist.
- Für jedes Modul muss getrennt für Stand und Fahrt eine Anzeigedauer einstellbar sein.
- Ein deaktiviertes Modul wird übersprungen.
- Ein aktiviertes, aber momentan nicht darstellbares Modul wird vorübergehend automatisch übersprungen.
- Sobald die benötigten Daten wieder verfügbar sind, nimmt das Modul automatisch wieder an der Rotation teil.
- Ist in einem Zustand nur ein Modul aktiv, bleibt es dauerhaft sichtbar.
- Ein Touch wechselt sofort zum nächsten im aktuellen Zustand erlaubten Modul und setzt den Zeitgeber zurück.
- Es gibt keinen erzwungenen Rücksprung zu einem bevorzugten Hauptmodul.

### Standardbelegung

| Modul | Stand | Fahrt |
|---|---:|---:|
| Uhr | aktiviert, 30 Sekunden | aktiviert, 30 Sekunden |
| Datum/Urlaub | aktiviert, 20 Sekunden | deaktiviert |
| Wetter | aktiviert, 20 Sekunden | deaktiviert |
| News | aktiviert, 15 Sekunden | deaktiviert |
| Karte | deaktiviert | aktiviert, 45 Sekunden |
| Himmel | aktiviert, 20 Sekunden | deaktiviert |

Diese Werte sind Ausgangseinstellungen und bleiben vollständig über die Weboberfläche änderbar.

### Szenenübergänge

- unmittelbares Umschalten ohne Schiebeanimation, damit Modulwechsel auf dem Raspberry Pi 3 flüssig bleiben
- keine weißen Zwischenbilder oder sichtbaren Ladezustände
- Module dürfen eigene, dezente Einblendanimationen besitzen
- Übergangsdauer und Effekte werden auf dem echten 1480×320-Display beurteilt und bei unruhiger, langsamer oder ruckeliger Wirkung angepasst

## 6. Funktionsmodule

### 6.1 Uhr und Themes

#### Muss-Anforderungen

- Anzeige im Format HH:MM:SS
- blinkende Doppelpunkte
- immer genau ein aktives Theme
- Theme-Auswahl über die Weboberfläche
- themeabhängige Optik, Anordnung und Animation
- später einfach ergänzbare Themes

#### Vorgesehene Themes

- Nixie neutral
- Nixie rot
- Nixie blau
- Klappziffernanzeige beziehungsweise Flip Clock

Nixie und Flip Clock werden als gleichwertige Themes derselben Uhr behandelt, nicht als getrennte Szenen.

### 6.2 Datums- und Urlaubsmodul

#### Muss-Anforderungen

- eigenständiges, spielerisch gestaltetes Modul
- sichtbare Darstellung des aktuellen Datums
- manuelle Eingabe von Urlaubszeiträumen über die Weboberfläche
- Verwaltung mehrerer Reisen beziehungsweise Urlaubszeiträume
- je Reise: Name, Beginn, Ende, optionaler Zielort und Aktiv-Schalter
- zusätzlich ein optionaler iCloud-Urlaubskalender über dessen öffentlichen Leselink; jeder Termin gilt als Urlaub
- Kalenderabruf alle 15 Minuten sowie manuell über die Einstellungen; Bearbeitung der importierten Termine erfolgt in Apple Kalender
- Übernahme von Titel, Zeitraum und Ort; ganztägige Termine, Zeitzonen, Wiederholungen und Ausnahmen werden berücksichtigt
- importierter Anzeigezeitraum: Vorjahr bis Ende des übernächsten Jahres, jährlich weitergeführt
- Kalenderänderungen und Löschungen ersetzen beim nächsten erfolgreichen Abruf den importierten Stand; manuelle Urlaube bleiben erhalten
- letzter erfolgreicher Kalenderstand wird transaktionssicher gespeichert und bei Abruffehlern mit Kennzeichnung weiterverwendet, auch nach Neustarts
- automatische Erkennung einer aktuell laufenden Reise
- während eines Urlaubs: grafischer Fortschritt von Urlaubsbeginn bis Urlaubsende
- der Urlaubsfortschritt wird ausschließlich zeitlich aus Beginn, aktuellem Datum und Ende berechnet
- ein GPS- oder entfernungsbasierter Reisefortschritt gehört nicht zum MVP
- außerhalb eines Urlaubs: grafischer Fortschritt durch das aktuelle Jahr
- außerhalb eines Urlaubs: kleine zusätzliche Countdown-Anzeige bis zur nächsten aktiven Reise
- für das breite Display geeignete horizontale Darstellung

#### Gestaltungsrichtung

- Jahres- beziehungsweise Reisezeitleiste
- kleiner Camper als möglicher Fortschrittsmarker
- Start, Heute und Ende beziehungsweise Monatsmarken

### 6.3 Wettermodul

#### Muss-Anforderungen

- eigenständiges Modul
- Standort automatisch aus der gemeinsamen GPS-Positionsschnittstelle
- aktuelles Wetter mit Temperatur, gefühlter Temperatur, Wetterzustand, Regenwahrscheinlichkeit und Wind
- Vorhersage für heute und die kommenden drei Tage
- je Vorhersagetag: Wettersymbol, Höchst- und Tiefsttemperatur sowie Regenwahrscheinlichkeit
- Sonnenaufgang, Sonnenuntergang und Mondphase bleiben dem eigenständigen Himmelsmodul vorbehalten
- verspielte, zum Wetterzustand passende Animationen, beispielsweise Sonne, Wolken oder Regen
- letzte erfolgreich geladene Wetterdaten dürfen bei Verbindungsproblemen höchstens zwei Stunden weiterverwendet werden
- bei zwischengespeicherten Daten wird der letzte Aktualisierungszeitpunkt dezent angezeigt
- ohne jemals geladene Daten oder nach Ablauf von zwei Stunden wird das Wettermodul automatisch übersprungen
- automatische Rückkehr in die Rotation, sobald wieder aktuelle Wetterdaten vorliegen

### 6.4 Newsmodul

#### Muss-Anforderungen

- eigenständiges Modul
- frei konfigurierbare RSS-Feeds
- Auswahl der Quellen über die Weboberfläche
- Zusammenführung der Beiträge aus mehreren aktivierten RSS-Feeds
- Darstellung jeweils einer großen, gut lesbaren Schlagzeile
- zusätzliche kleine Anzeige von Quelle und Veröffentlichungszeit
- einstellbare Wechselzeit zwischen den Schlagzeilen
- kein längerer Anreißertext im MVP
- Aktualisierung der RSS-Feeds alle 15 Minuten
- Zusammenführung der 20 neuesten verfügbaren Schlagzeilen
- keine dauerhafte Zwischenspeicherung von Nachrichten
- automatisches Überspringen des Newsmoduls, wenn keine aktuellen RSS-Daten geladen werden können
- automatische Rückkehr in die Rotation, sobald RSS-Daten wieder verfügbar sind

### 6.5 Kartenmodul

#### Muss-Anforderungen

- eigenständiges Modul
- aktuelle Fahrzeugposition aus der gemeinsamen GPS-Schnittstelle
- getrennt für Stand und Fahrt aktivierbar
- während der Fahrt Ausrichtung der Karte in Fahrtrichtung und zentrierte Fahrzeugposition
- im Stand Ausrichtung mit Norden oben
- gut sichtbare Anzeige der aktuellen Geschwindigkeit
- Aufteilung der Anzeige in 80 Prozent Karte und 20 Prozent Fahrdaten
- gut sichtbare Anzeige der aktuellen GPS-Höhe; ohne gültigen 3D-Fix darf kein veralteter Höhenwert stehen bleiben
- dezente Anzeige der aktuellen Straße, sofern die Information verfügbar ist
- geschwindigkeitsabhängige, fließende Zoomstufe
- Zoomparameter über die Weboberfläche einstellbar
- GPS-Funktion und andere Module dürfen bei fehlender Onlinekarte nicht ausfallen
- kein eigener Offline-Kartendownload im MVP
- bereits geladene Kartenbereiche dürfen im normalen Browser-Cache verbleiben
- bei fehlender Verbindung Anzeige des letzten verfügbaren Stands oder eines klaren Offline-Hinweises

Eine zusätzliche Richtungsanzeige gehört nicht zum MVP. Ein gezielter Download von Reisekarten kann später ergänzt werden.

### 6.6 Himmel

Das Himmelsmodul stellt Sonnen- und Monddaten als eigenständiges optionales Modul im Stil der Wetteransicht dar.

#### Muss-Anforderungen

- im Stand standardmäßig aktiviert und während der Fahrt standardmäßig deaktiviert
- wie jedes Modul frei aktivierbar und mit eigener Anzeigedauer für Stand und Fahrt
- automatische Standortbestimmung über die gemeinsame GPS-Schnittstelle
- hochwertige, spielerische Grafiken statt einer rein tabellarischen Informationsansicht
- Nutzung nahezu der gesamten Displaybreite von 1480 Pixeln
- panoramaartige Darstellung des Sonnenverlaufs mit grafischer Position der Sonne
- gut integrierte Anzeige von Sonnenaufgang und Sonnenuntergang
- Anzeige von Tageslänge, aktuellem Sonnenstatus und verbleibender Zeit bis zum nächsten Sonnenereignis
- Anzeige von Mondaufgang und Monduntergang
- grafische Mondphase mit Bezeichnung, Beleuchtungsgrad und Status über beziehungsweise unter dem Horizont
- optische Anpassung an den aktuellen Tages- beziehungsweise Nachtzustand
- gemeinsame Online-Datenabfrage und zweistündige Gültigkeit mit dem Wettermodul
- automatisches Überspringen bei fehlenden oder abgelaufenen Online-Daten

### 6.7 Spätere Spielereien

- eigenständiges GPS-/Entfernungsmodul für den Fortschritt zwischen Start und Ziel
- Neigungsanzeige im Stand
- digitale Wasserwaage
- G-Kugel während der Fahrt
- künstlicher Horizont
- Kompass und weitere IMU-basierte Animationen

Diese Funktionen gehören nicht zum MVP, ihre spätere Ergänzung darf jedoch keinen grundlegenden Umbau erfordern.

## 7. GPS und Simulation

### Muss-Anforderungen

- eine gemeinsame Positionsschnittstelle für alle Module
- Betriebsart „Real“ für Router-GPS/GNSS
- Betriebsart „Simulation“ für Entwicklung und Tests ohne Camper
- Eingabe einer festen Position per Ort oder Koordinaten
- einstellbare simulierte Geschwindigkeit und optionale Höhe
- simulierte Geschwindigkeiten durchlaufen dieselbe Stand-/Fahrt-Erkennung wie reale GPS-Daten
- zusätzliche Testschalter zum Erzwingen der Zustände „Stand“ und „Fahrt“
- automatische Rückkehr zum Router-GPS nach Beenden der Simulation
- später optional: Fahrtrichtung und abspielbare Teststrecke
- Module dürfen nicht unterscheiden müssen, ob Daten real oder simuliert sind

### Zeitzone

- Die Uhrzeit stammt grundsätzlich aus der Systemzeit des Raspberry Pi.
- Nach einem vollständigen Stromverlust wird die Systemzeit automatisch über das Internet synchronisiert.
- Solange noch keine zuverlässige Zeitsynchronisierung bestätigt wurde, zeigt das Uhrmodul keine möglicherweise falsche Uhrzeit, sondern „Zeit wird synchronisiert“ oder eine gleichwertige grafische Darstellung.
- Im Automatikmodus wird die Zeitzone anhand einer stabilen GPS-Position bestimmt.
- Kurze GPS-Aussetzer oder unplausible Positionssprünge dürfen keine Zeitzonenänderung auslösen.
- Bei GPS-Ausfall bleibt die zuletzt gültige Zeitzone erhalten.
- Über die Weboberfläche kann alternativ eine feste Zeitzone gewählt werden.
- Die zuletzt ermittelte beziehungsweise manuell gewählte Zeitzone wird dauerhaft gespeichert.
- Eine batteriegepufferte Echtzeituhr gehört nicht zum MVP und kann später ergänzt werden, falls ein korrekter Offline-Kaltstart erforderlich wird.

## 8. Konfiguration

Mindestens folgende Einstellungen müssen über die Weboberfläche erreichbar sein:

- aktives Uhr-Theme und themeabhängiger Hintergrund
- Modul aktiv/inaktiv für Stand und Fahrt
- Modulreihenfolge
- Anzeigedauer je Modul für Stand und Fahrt
- tägliches Aktivzeitfenster im Stand
- Dauer des manuellen Aufweckens
- Displaygröße
- getrennte Helligkeitswerte für Stand und Fahrt
- GPS-Modus, Routeradresse und Port
- automatische oder feste Zeitzone
- simulierte Position, Geschwindigkeit und Höhe
- Wettereinheit
- RSS-Quellen
- mehrere Urlaubszeiträume mit Name, Beginn, Ende, optionalem Zielort und Aktiv-Schalter
- Karten-Zoomparameter
- gemeinsame Deckkraft der Informationsrahmen in Wetter, Himmel sowie Datum und Urlaub
- gemeinsame einstellbare Hintergrund-Unschärfe innerhalb dieser Informationsrahmen

## 9. Stromausfallfestigkeit und Datenhaltung

### Kernanforderung

Das System muss häufige unerwartete Spannungsunterbrechungen möglichst ohne beschädigte Anwendung oder Konfiguration überstehen.

### Muss-Anforderungen

- automatische Wiederaufnahme nach dem Einschalten
- automatischer Neustart des Backend-Dienstes nach einem Fehler
- persistente Daten nur in einem klar abgegrenzten Datenverzeichnis
- atomare beziehungsweise transaktionssichere Speicherung
- SQLite im WAL-Modus mit vollständiger Synchronisierung
- Begrenzung unnötiger Schreibzugriffe auf die SD-Karte
- temporäre Fahrspur- und Sensordaten möglichst nur im RAM
- normale Laufzeitprotokolle nur in einem größenbegrenzten RAM-Ringspeicher
- keine dauerhafte Speicherung von GPS-Strecken, Positionsverläufen oder Bewegungsprofilen
- dauerhafte Speicherung ausschließlich notwendiger Einstellungen, Theme-, Modul-, Urlaubs- und Konfigurationsdaten
- aktuelle Fehlerprotokolle müssen bei Bedarf per SSH auslesbar sein
- keine Abhängigkeit der Uhr von einer funktionierenden Internetverbindung

### Soll-Anforderungen

- High-Endurance-SD-Karte
- schreibgeschütztes Root-Dateisystem oder gleichwertiger DietPi-Dateisystemschutz nach gesonderter Prüfung und Sicherung
- definierter Wiederherstellungs- und Sicherungsweg

Ein Import oder Export der Konfiguration über die Weboberfläche gehört nicht zum MVP. Technische Sicherungen vor Updates erfolgen über SSH.

## 10. Softwarearchitektur

- lokaler FastAPI-Webserver als Backend
- HTML-, CSS- und JavaScript-Frontend im Chromium-Kiosk
- feste 1480×320-Designfläche mit Skalierung für Testbrowser
- getrennte Frontendmodule mit gemeinsamem Modulvertrag
- zentrale Szenensteuerung
- gemeinsame Status- und Positionsschnittstellen
- persistente Konfiguration in SQLite
- externe Datenquellen mit Zeitlimit, Cache und Offline-Fallback
- Gesundheitsendpunkt für Startreihenfolge und Diagnose

Die Helligkeit soll bevorzugt über die tatsächliche Hintergrundbeleuchtung des Displays geregelt werden. Unterstützt die Hardware dies nicht, muss die Webanwendung die Darstellung ersatzweise visuell abdunkeln können.

## 10.1 Leistung und Darstellungsqualität

- Auf dem Raspberry Pi 3 müssen Animationen stabil mit mindestens 30 Bildern pro Sekunde dargestellt werden.
- 60 Bilder pro Sekunde sind wünschenswert, aber keine Abnahmevoraussetzung.
- Stabilität, lesbare Darstellung und geringe Prozessorlast haben Vorrang vor aufwendigen Effekten.
- Reicht die Leistung nicht aus, dürfen Animationen und grafische Effekte automatisch vereinfacht werden.
- Eine Leistungsanpassung darf weder Informationen ausblenden noch die Touchbedienung beeinträchtigen.
- Die tatsächliche Wirkung und Flüssigkeit wird auf dem eingebauten 1480×320-Display geprüft.

## 11. Autostart und Wartung

### Muss-Anforderungen

- Backend startet automatisch beim Booten.
- Der Backend-Dienst wird bei einem Absturz automatisch neu gestartet.
- Chromium wartet beim Boot auf ein gesundes Backend und öffnet anschließend die Kioskseite.
- Die Anwendung ist per SSH wartbar.
- Vor Installationen muss ein Rücksprung auf den vorherigen Stand möglich sein.
- Weder DietPi noch das Camper-Display führen unbeaufsichtigte automatische Updates durch.
- System- und Anwendungsupdates erfolgen ausschließlich geplant über SSH.
- Vor jedem Update wird der laufende Stand gesichert.
- Nach jedem Update werden Gesundheitsprüfung, Anzeige und Autostart kontrolliert.
- Sicherheitsupdates werden gesammelt in geplanten Wartungsfenstern eingespielt.
- Systemänderungen mit erhöhtem Risiko, insbesondere Overlay-Dateisystem, Partitionierung und vollständige Systemupdates, erfolgen nur nach ausdrücklicher Freigabe.

## 12. Aktueller Umsetzungsstand

### Bereits lauffähig (Camper-Display v0.5.0)

- DietPi, Chromium-Kiosk und 1480×320-Ausgabe
- FastAPI-Backend als Autostart-Dienst
- Uhr mit HH:MM:SS und mehreren Nixie-/Flip-Themes
- eine gemeinsame Modulreihenfolge mit getrennter Aktivierung und Anzeigedauer für Stand und Fahrt
- zentrale Zustandslogik für Fahrt, Stand, Nachtplan und manuelles Aufwecken
- Tippen zum Weiterschalten, Wischen vor/zurück und erster Touch zum reinen Aufwecken
- Wetter mit Panoramaansicht, aktueller Temperatur, gefühlter Temperatur, Wind sowie Vier-Tage-Vorhersage einschließlich Regenwahrscheinlichkeit und Regenmenge
- Himmel mit Tages-/Nachtpanorama, Sonnenbogen, Auf- und Untergangszeiten, Tageslänge, Mondphase, Beleuchtungsgrad und Horizontstatus
- Datum und Urlaub mit laufendem rein zeitlichem Urlaubsfortschritt, astronomischer Jahreszeiten-Zeitleiste, Urlaubsmarkierungen und Countdown zur nächsten Reise
- beliebig viele dauerhaft gespeicherte Urlaubszeiträume mit Name, Beginn, Ende, optionalem Ziel und Aktiv-Schalter in der Web-Konfiguration; keine automatische Löschung zum Jahreswechsel
- optionale iCloud-Urlaubsübernahme mit Freigabelink, Abrufstatus, manueller Aktualisierung und stromausfallfestem Offline-Stand
- Karte mit zweigeteilter Karten-/Fahrdatenansicht, Strecke, Sonnen- und Mondanzeige; das vorhandene Streckenmodul wird für das MVP deaktiviert
- Web-Konfiguration für Modulreihenfolge, Stand-/Fahrtfreigaben, Laufzeiten, Helligkeit und Zustandsgrenzen
- unmittelbare, ressourcenschonende Modulwechsel sowie einstellbare gemeinsame Deckkraft und Hintergrund-Unschärfe der Informationsrahmen
- GPS-Ortssimulation einschließlich Geschwindigkeit sowie erzwungenem Stand-, Fahrt- und Automatikmodus
- SQLite-Datenhaltung mit WAL
- Gesundheitsprüfung und fehlertoleranter Modulstart
- vorbereitetes, standardmäßig deaktiviertes Newsmodul

### Noch umzusetzen oder anzupassen

- RSS-Newsmodul
- Erweiterung der Web-Konfiguration um RSS-Quellen und automatische Zeitzone
- abschließender Stromausfall- und Boot-Test

## 13. Abnahmekriterien für das MVP

Das MVP ist abnahmefähig, wenn:

1. die Anwendung nach dem Einschalten ohne Benutzereingriff startet,
2. die Uhr auf 1480 × 320 korrekt und flüssig dargestellt wird,
3. Stand und Fahrt zuverlässig unterschieden werden,
4. Modulfreigabe und Anzeigedauer je Zustand funktionieren,
5. Touch aufweckt und zum nächsten erlaubten Modul schaltet,
6. Theme, Aktivzeiten, Module, GPS-Simulation, Wetter, Newsquellen und Urlaub über die Weboberfläche konfigurierbar sind,
7. Wetter, News oder Kartenfehler die Uhr nicht beeinträchtigen,
8. gespeicherte Einstellungen einen normalen Stromausfall überstehen,
9. Backend und Kiosk nach einem Neustart wieder selbstständig betriebsbereit sind.

## 14. Offene Entscheidungen

Es bestehen keine offenen fachlichen MVP-Entscheidungen. Die technische Ansteuerung der Displaybeleuchtung wird noch am realen Display geprüft; falls keine Hardwaresteuerung möglich ist, greift die festgelegte visuelle Abdunklung.
