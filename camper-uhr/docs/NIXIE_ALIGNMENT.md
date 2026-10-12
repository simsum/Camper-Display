# Ruhige Nixie-Röhren – lokale Vorschau

Stand 11.09.2026: Vom Benutzer freigegeben und als Version 0.5.1 auf [Pi-IP] installiert.

Prüfstand: 20 Ziffernwechsel im Browser bestanden; JavaScript-Syntaxprüfung bestanden. Alle 29 Backend-Tests in separatem Staging mit der vorhandenen Pi-Python-Umgebung bestanden. Nach Installation Healthcheck 0.5.1 und Vergleich sämtlicher Einstellungen erfolgreich (nur entfernte Designs dürfen auf Flip wechseln). Der lokale vollständige Testlauf war zuvor wegen fehlendem `httpx` nicht ausführbar.

Vollständige Sicherung vor Installation: `private Sicherung auf dem Pi; vertraulicher Pfad hier nicht veröffentlicht`, einschließlich konsistenter SQLite-Sicherung, privatem Einstellungsvergleich und vorherigem Kiosk-Startskript. Entfernte aktive Bildserien ebenfalls dort gesichert. Kiosk-Buildkennung auf 0.5.1 erhöht und Pi zum Neuladen neu gestartet. Keine Paket- oder Betriebssystemupdates.

Offener Abschlusscheck: Nach dem angeforderten Neustart blieb [Pi-IP] bei wiederholten SSH-, HTTP- und Ping-Prüfungen nicht erreichbar; kein ARP-Eintrag. Installation und Einstellungsvergleich waren vor dem Neustart erfolgreich. Kiosk-Start und Bildausrichtung nach Neustart sind noch nicht bestätigt; Rückmeldung vom physischen Display angefragt.

Die PNGs besitzen innerhalb einer Serie dieselben Außenmaße, enthalten aber unterschiedlich große und versetzte Gehäuse. Deshalb kann eine feste IMG-Breite allein das Springen nicht beheben.

Der neue Nixie-Renderer verwendet pro Design ein unveränderliches Gehäuse und ein festes inneres Ziffernfenster. Die Originalbilder werden nur für den jeweiligen Fensterinhalt verwendet. Alle Ziffernebenen laden beim Aufbau; beim Wechsel ändert sich ausschließlich ihre Sichtbarkeit. Die neue Ebene wird erst sichtbar, wenn das Bild geladen ist. Glas, Sockel, Befestigung und Dekoration wechseln nicht mehr mit der Zahl.

`NIXIE_ALIGNMENT` in `frontend/js/themes.js` enthält Quell- und Zielrechtecke in Pixelkoordinaten der Originalbilder. `deploy/measure-nixie.py` ermittelt sie aus manuell eingegrenzten Elektrodenbereichen und den leuchtenden Ziffern; das Skript liest PNGs ausschließlich und gibt Metadaten aus. Die Originalbilder werden nicht verändert. Beide Nixie-Designs verwenden das leere Gehäuse aus `colon_off.png`. Die Ziffernformen und das innere Drahtgitter stammen weiterhin aus den Originalen.

Es bleiben ausschließlich **Flip, Blau und Schlicht**. Die Klappzahlen-Uhr verwendet unverändert den bisherigen Bildrenderer. Das CSS-Theme wurde entfernt; die Bildserien Klassisch, Blau XL und Blau + Eule liegen nur noch zur Wiederherstellung unter `archive/retired-clock-themes`, außerhalb des Frontends. Bestehende Einstellungen mit entfernten Designs wechseln beim Laden auf Flip, alle übrigen Einstellungen bleiben erhalten.

Blau erhält eine feste CSS-Außenkontur gegen störende Freistellungsreste. Beide Röhrendesigns erhalten einen dezenten statischen Kontakt-/Lichtschein unter dem Sockel; Hintergrundfarben bleiben frei wählbar. Keine PNG-Bearbeitung und keine neue Animation. Die Ziffernausrichtung bleibt unverändert.

`previews/nixie-alignment.html` zeigt Vorher/Nachher, die drei Designs, Hintergrundfarbwahl, manuelles Weiterschalten und eine Zifferngalerie. „Alle Ziffern prüfen“ prüft alle 20 Kombinationen der zwei Nixie-Designs auf unveränderte Gehäuse-/Fensterkoordinaten sowie vollständig geladene sichtbare Ziffern. Backend-Tests prüfen die drei erlaubten Designs und die Migration alter Einstellungen.
