# Arbeitsstand Camper-Display

## Öffentliche Projektfassung · Oktober 2026

Modulare Anzeige für Raspberry Pi 3 / DietPi, festes Layout 1480 × 320 Pixel.
Backend: FastAPI und SQLite. Frontend: HTML/CSS/JavaScript im Chromium-Kiosk.
Die API meldet weiterhin die interne Versionsnummer 0.6.5; spätere Funktionen
sind im Quellcode und in den Moduldokumenten enthalten. Es handelt sich um einen
Entwicklungsstand, nicht um ein fertig geprüftes Installations-Image.

## Funktionsstand

- Sieben Uhrmodule: Flip, Blau, Schlicht, Panorama, Bahnhofs-LED, Linear, Kugelbahn.
- Wetter mit Ortsnamen, Himmel, Datum und Urlaub mit optionalem Kalenderfeed.
- Karte mit Fahrtrichtung, gefiltertem GPS und Stand-/Fahrtzuständen.
- Traccar-Fahrtübersicht und Ankunftsanzeige mit Quellenhinweisen.
- Nachtmodus, Zeitplan, Touch-Aufwecken und Helligkeit.
- Reisemomente: lokale Fotoverwaltung, adaptive Bildgruppen, Bilddatum und Ort.
- Foto-Link und QR-Code werden lokal erzeugt. Beim Kiosk über localhost muss
  `CAMPERDISPLAY_PUBLIC_URL` auf die vom Handy erreichbare LAN-Adresse zeigen.
- Neue Traccar-Konfigurationen enthalten keine voreingestellte Serveradresse.

## Entwicklung und Betrieb

Quellcode unter `camper-uhr/`; Tests über `scripts/test_local.py`.
Der Windows-Starter verwendet separate Daten unter `camper-uhr/.local/data/`
und simuliert Displayhardware. Keine Übernahme von Produktionsdaten für Tests.
Die öffentliche Dokumentation enthält nur Beispieladressen und Standardpfade.

Der vorhandene Pi wird durch Änderungen am Repository nicht automatisch aktualisiert.
Vor jeder Installation aktuellen Zugriff, Datenpfade, Dienste, Display und Touch
prüfen und private Laufzeitdaten sichern. Keine automatischen Systemupdates,
kein ungeprüftes Überschreiben der Einstellungen. Hardwareinstallation und
Displaydrehung sind gerätespezifisch; sie benötigen einen separaten Test am Gerät.

Die vorangegangene interne Übergabe bleibt ausschließlich in der lokalen,
nicht versionierten Sicherung erhalten. Private Archive sind keine Projektanweisungen.
