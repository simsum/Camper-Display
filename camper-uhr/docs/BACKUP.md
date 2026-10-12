# Sicherung und Wiederherstellung

Git sichert Quellcode und Dokumentation. Einstellungen, Kalenderdaten,
Traccar-Zugang und Reisefotos müssen gesondert und vertraulich gesichert werden.

## Zu sichernde Daten

- Der tatsächlich konfigurierte Ordner `CAMPERDISPLAY_DATA_DIR`.
- Gegebenenfalls die gesondert konfigurierte `CAMPERDISPLAY_VACATION_DB`.
- Lokale Dienstkonfiguration und gerätespezifische Display-/Touch-Einstellungen.

Der Entwicklungsstarter verwendet `.local/data/`; für den Pi ist
`/var/lib/camperdisplay` ein üblicher Datenpfad. Vor einer Sicherung den
wirklichen Pfad anhand der Dienstkonfiguration prüfen.

SQLite bei gestopptem Dienst zusammen mit den zugehörigen Dateien sichern oder
die SQLite-Backup-API verwenden. Eine laufende Datenbank nicht isoliert von ihrem
WAL-Zustand kopieren. Fotos und Metadaten gehören ebenfalls zur Sicherung.
Sicherungen enthalten vertrauliche Daten und gehören weder in das Repository
noch in öffentliche Releases. Geschützt auf einem getrennten Datenträger lagern.

## Wiederherstellung

1. Zielinstallation und Version prüfen; Backend stoppen.
2. Den bestehenden Zielstand sichern, bevor Dateien ersetzt werden.
3. Zusammengehörige Datenbank- und Fotodaten wiederherstellen. Keine neue DB mit
   alten WAL-/SHM-Dateien mischen. Dateirechte und Dienstbenutzer berücksichtigen.
4. Dienst starten und `/api/health`, Einstellungen und Fotoverwaltung prüfen.
5. Kalender, Traccar, GPS und die gerätespezifische Anzeige separat testen.

Historische Exportarchive und interne Sicherungswerkzeuge sind nicht Teil der
öffentlichen Installationsanleitung.
