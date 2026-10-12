# Nachtmodus – lokal, noch nicht auf dem Pi

Die Nachtuhr verwendet die freigegebene Gestaltung: Schwarz, Bernstein (alternativ Rot oder Warmweiß), maximal große HH:MM ohne Sekunden oder Animation. Die tatsächlichen Glyphenmaße bestimmen die Größe; alle Ziffern teilen eine stabile Geometrie mit etwa 12 Pixeln Rand oben/unten bei 1480 × 320. Neuzeichnen nur bei Minuten-/Format-/Farbwechsel.

Einstellungen unter „Nachtmodus und Display-Zeitplan“:

- Nachtuhr / Display aus / normale Anzeige; Zeitplan gilt wie bisher nur im Stand.
- Neue Standardkonfiguration: 22:30–07:00, Nachtuhr, Bernstein, 5 %, 30 Sekunden Touch-Aufwecken.
- Bestehende Zeitpläne, Aktivierung und bisheriges „Display aus“ bleiben bei Migration erhalten. Für die neue Funktion dort „Nachtuhr“ auswählen. Keine vorhandenen Benutzerwerte werden überschrieben.
- Eigene Nachthelligkeit 1–100 %, eigene Aufweckdauer 5–600 Sekunden. Gleiche Start- und Endzeit deaktiviert das Fenster.
- Touch zeigt normale Module und normale Stand-Helligkeit. Weitere Berührungen verlängern die Wachzeit. Danach kehrt die Nachtuhr zurück. Während der Fahrt bleibt die normale Fahrtanzeige aktiv.
- Manuelles „Screen aus“ ist bis „Screen an“ verriegelt, unabhängig vom Zeitplan und von Touch. Die Verriegelung ist nur im Arbeitsspeicher; nach Dienst-/Pi-Neustart gilt wieder der Zeitplan. „Screen an“ hebt sie auf und gewährt nachts eine kurze Wachzeit.

## Helligkeit und Hardware

Die bisherige Anwendung verwendet eine schwarze Abdunklungsebene, keine Hardware-Helligkeitssteuerung. Der neue Nachtwert nutzt diese als Ersatz. Ein optionaler Linux-Backlight-Adapter ist vorbereitet: erst nach Prüfung des konkreten Displays `CAMPERDISPLAY_BACKLIGHT_DIR=/sys/class/backlight/<bestätigtes-Gerät>` in der Dienstumgebung konfigurieren. Kein automatisches Suchen oder Ändern von Systemkonfiguration, keine neuen Pakete. Bei fehlender/unzugänglicher Schnittstelle bleibt Software-Abdunklung aktiv; erfolgreiche Hardware-Regelung wird im Status gemeldet und verhindert doppelte Abdunklung im Kiosk. Ein HDMI-Display ohne solche Schnittstelle benötigt gegebenenfalls eine andere, gerätespezifische Anbindung. Diese ist noch nicht geprüft.

Scheduler, Touch-Watcher und manuelle Schaltungen teilen eine Sperre; fehlgeschlagene xrandr-Aufrufe werden nicht als erfolgreiche Schaltung gemeldet. Einschalten erhält die bestätigte Linksrotation. Die Anzeigeentscheidung kommt aus dem Backend; bei dessen Ausfall läuft eine bereits angezeigte Nachtuhr lokal weiter, Zeitplan-/Touch-Umschaltungen benötigen jedoch das Backend.

## Prüfungen

`test_night_mode.py`: Zeitgrenzen über Mitternacht, Tagesfenster, gleicher Start/Ende, Fahrt, deaktivierter Zeitplan, drei Nachtverhalten, Touch, manuelle Priorität, fehlerhafte Hardware-Schaltung, Validierung, Migration und Backlight-Fallback. App-Test: Modulrotation/Animationen pausieren, lokale Nachtuhr tickt, manuell ausgeschaltet kein Tick, Rückkehr zum bisherigen Modul, keine doppelte Hardware-/Software-Abdunklung. `previews/night-mode.html` nutzt den Produktionsrenderer und prüft zehn Uhrzeit-/Formatfälle anhand der tatsächlich gezeichneten Pixel auf Randabstand und maximale Höhe.

Die physische Displayhelligkeit, Touch und das Einschalten am Pi sind noch am Gerät zu prüfen. Kein Pi-Deployment und keine Änderung seiner Systemkonfiguration in diesem Schritt.

Lokaler Prüfstand: 18 fokussierte Python-Tests bestanden (Nachtmodus, Display-Schaltung, Uhrkonfiguration/-Themes, Settings-Store), drei Node-Testsuiten für App, Kugelbahn und moderne Uhren bestanden. Browserprüfung: zehn gerenderte Zeit-/Formatfälle bestehen die Pixelprüfung; Vorschau visuell geprüft. Vollständige Backend-/Geräteprüfung weiterhin ausstehend.
