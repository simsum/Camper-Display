# Einstellungen · Version 0.6.4 · auf Pi installiert

Nachtrag 0.6.5: Ankunftswartezeit jetzt in Sekunden (bestehende 5 Minuten → 300
Sekunden). Ankunftstest verwendet das Ortsfeld der GPS-Simulation; Details und
Migrations-/Testnachweis in `ARRIVAL_MODE.md`. Layout weiterhin wie unten.

Stand 11.09.2026. Nutzer bestätigte zuvor Anfo-Testankunft am echten Display.

Sechs native, standardmäßig geschlossene Aufklappbereiche: Module & Reihenfolge,
Anzeige & Nachtmodus, Urlaub & Ankunft, Karte & Wetter, Verbindungen, Erweitert &
Tests. Vorhandene Bedienelemente werden ohne Ersetzung umgruppiert; IDs und
Aktionshandler bleiben erhalten. Anfo-Test und GPS-Simulation unter Tests.

Feste Speichern-Leiste: Vergleich mit dem letzten gespeicherten Stand, Hinweis
auf offene Änderungen, deaktivierter Button ohne Änderungen bzw. während PUT,
Warnung beim Verlassen mit offenen Änderungen. Änderungen während eines PUT sind
gesperrt; fehlgeschlagene Speicherung behält Eingaben/Änderungshinweis. Traccar
ist ausdrücklich separat zu speichern und nicht Bestandteil des globalen PUT.
Keine Einstellungen/Zugangsdaten im Browser-Storage. Testbedienung zählt nicht
als Änderung allgemeiner Einstellungen.

Auflösung fest im Backend-Code: `models.DISPLAY_WIDTH=1480`, `DISPLAY_HEIGHT=320`.
Die API-Felder bleiben kompatibel erhalten, sind aber eingefroren und eingehende
Werte werden vor Validierung auf die Konstanten gesetzt. Alte gespeicherte Werte
werden beim Laden vereinheitlicht. Keine editierbaren Auflösungsfelder mehr.
Keine Änderung an HDMI-/Touch-/Systemkonfiguration.

Prüfungen: 72 Python-Tests auf Pi erfolgreich; neue Tests prüfen Defaults,
abweichende/ungültige Altwerte, eingefrorene Felder und Erhalt übriger Einstellungen.
JS-Syntax geprüft. Isolierter Loopback-Testserver `tests/settings_ui_server.py`
(Port 8768, nur RAM-Testdaten, keine Pi-/GPS-/Tokenverbindung) für Browserprüfung:
Bereiche, erfolgreiche Speicherung, Änderungshinweis, Wiederherstellung nach
Speicherfehler, Rücknahme einer Änderung, Desktop und mobile Ansicht 390x844.
Produktionsseite anschließend direkt vom Pi geladen: sechs Bereiche und sauberer
gespeicherter Zustand bestätigt, ohne Tests an echten Einstellungen auszuführen.

Installation 0.6.4: Backup `private Sicherung auf dem Pi; vertraulicher Pfad hier nicht veröffentlicht` mit
Code, konsistenter SQLite-Kopie und privatem Einstellungsvergleich. Nur Backend
neu gestartet, kein Kiosk-/Pi-Neustart. Health ok. Exakter Vergleich bestätigt
alle übrigen Einstellungen unverändert. Kioskstarter zuletzt 0.6.3; für dieses
reine Settings-/Backend-Update unverändert, HTML-Einstieg weiterhin no-store.
