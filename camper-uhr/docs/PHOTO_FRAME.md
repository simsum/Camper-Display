# Digitaler Bilderrahmen â€“ Reisemomente

Stand 20.09.2026: Die adaptive Ausbaustufe ist nach verifizierter Sicherung auf dem Pi installiert. Sie gruppiert ausschlieÃŸlich Hochformate und zeigt Quadrat- sowie Querformate einzeln. Reisemomente startet nur manuell fÃ¼r eine gewÃ¤hlte Dauer. Die Darstellung wurde mit allen 42 vorhandenen Fotos geprÃ¼ft.

## Bedienung

Die Fotoseite ist unter `/photos` erreichbar und zusÃ¤tzlich in den Einstellungen verlinkt. Auf iOS und Android Ã¶ffnet â€žFotos auswÃ¤hlenâ€œ die jeweilige System-Fotoauswahl. Mehrere Bilder kÃ¶nnen in einem Schritt gewÃ¤hlt werden. Der Browser verkleinert jedes Bild auf hÃ¶chstens 1920 Ã— 1280 Pixel und wandelt es vor dem Upload in JPEG um. Dadurch werden Netzwerk, SD-Karte und Raspberry Pi entlastet. Ob HEIC direkt dekodiert werden kann, hÃ¤ngt vom mobilen Browser ab und muss noch auf einem echten iPhone geprÃ¼ft werden.

Die Einstellungen enthalten eine eigene, aufklappbare Gruppe â€žReisemomenteâ€œ. Die Anzeigedauer wird wie bei den Ã¼brigen zeitgesteuerten Funktionen in Sekunden eingestellt (30 bis 3600). â€žReisemomente anzeigenâ€œ startet die PrÃ¤sentation, â€žReisemomente beendenâ€œ kehrt sofort zur normalen Anzeige zurÃ¼ck. Dieselben Bedienelemente stehen direkt auf der Fotoseite. Nach Ablauf der Zeit endet die PrÃ¤sentation automatisch.

Alle Uhrmodule besitzen im Stand unten links eine unsichtbare TouchflÃ¤che von 180 Ã— 90 Pixeln. Ein Antippen Ã¶ffnet fÃ¼r 90 Sekunden eine groÃŸe QR-Ansicht zur Fotoseite unter der konfigurierten LAN-Adresse mit Pfad `/photos`. Antippen der QR-Ansicht schlieÃŸt sie sofort. Die TouchflÃ¤che ist wÃ¤hrend der Fahrt und auf Nicht-Uhrmodulen abgeschaltet. Der QR-Code wird lokal erzeugt und über `/api/photos/qr.svg` ausgeliefert; es wird kein externer QR-Dienst aufgerufen.

Die Seite zeigt alle gespeicherten Fotos und erlaubt deren einzelne LÃ¶schung. Upload und LÃ¶schung akzeptieren nur gleichursprÃ¼ngliche Anfragen. Es werden JPEG, PNG und WebP angenommen, maximal 8 MB je Datei, 500 Dateien und insgesamt 2 GB. ZufÃ¤llige Dateinamen verhindern die Verwendung Ã¼bermittelter Pfade. Dateien liegen ausschlieÃŸlich im privaten Anwendungsdatenordner unter `photos/` und werden mit Benutzerrechten 0600 angelegt.

Zum LÃ¶schen wird das Ã— am Foto angetippt. Der Knopf wird anschlieÃŸend rot und zeigt â€žLÃ¶schen?â€œ. Erst ein zweites Tippen lÃ¶scht das Bild. Erfolg oder Fehler wird oberhalb der Fotoliste angezeigt; ein nativer Browser-BestÃ¤tigungsdialog wird bewusst nicht verwendet.

## PrÃ¤sentation

Reisemomente ist kein Teil der automatischen Modulrotation. Der manuelle Modus wird nur im Stand angezeigt. Fahrtmodus, Ankunftsanzeige und ausgeschaltetes Display beziehungsweise Nachtmodus haben Vorrang.

Der Pi ermittelt fÃ¼r JPEG, PNG und WebP Breite, HÃ¶he und SeitenverhÃ¤ltnis. AusschlieÃŸlich echte Hochformate mit einem SeitenverhÃ¤ltnis unter 1 werden in ihrer zeitlichen Reihenfolge zu Gruppen von bis zu fÃ¼nf Fotos zusammengestellt. Quadratische Bilder, normale Querformate und Panoramen erhalten jeweils eine eigene Seite. Jede Seite wechselt nach acht Sekunden.

Alle Bilder verwenden `object-fit: contain` und bleiben vollstÃ¤ndig sichtbar. Hochformatgruppen nutzen die volle DisplayhÃ¶he und ihre natÃ¼rlichen Breiten. Freie RestflÃ¤chen werden mit einer abgedunkelten, weichgezeichneten Version des aktuellen Fotos gefÃ¼llt. Dadurch entstehen keine harten leeren RÃ¤nder, ohne Bildteile abzuschneiden.

Der frÃ¼here globale Titel, das Ãœbertragungsdatum und der BildzÃ¤hler sind entfernt. Neue Uploads lesen vor der Verkleinerung das EXIF-Aufnahmedatum und vorhandene GPS-Koordinaten. Ohne EXIF-Datum wird das Dateidatum verwendet. Der Pi lÃ¶st GPS einmalig Ã¼ber OpenStreetMap/Nominatim zu Gemeinde und Land auf und speichert nur Aufnahmedatum und Ortsname in einer privaten JSON-Seitendatei mit Rechten 0600; die Koordinaten werden nicht dauerhaft gespeichert. Jedes Foto zeigt seine vorhandenen Angaben sehr klein und halbtransparent unten links. Fehlen Angaben, bleibt die Einblendung vollstÃ¤ndig unsichtbar. Bereits vor dieser Erweiterung hochgeladene Fotos besitzen keine ursprÃ¼nglichen EXIF-Daten und zeigen deshalb keine ersatzweise aktuelle Datumsangabe.

Lokale Gestaltungsvorschau: `/photo-preview.html`. Sie verwendet vorhandene Projektbilder als Beispieldaten und speichert nichts.

## Noch offen

- Praktischen Scan des automatisch erzeugten QR-Codes und Uploadtest mit iOS/HEIC und Android durchführen.
- Verhalten bei knappem SD-Speicher weiter verbessern.

PrÃ¼fung: 93 Python-Tests lokal und erneut im Pi-Staging sowie alle vorhandenen JavaScript-Tests bestanden. ZusÃ¤tzliche Tests decken Bildabmessungen, adaptive Seitenbildung, Formate, GrÃ¶ÃŸenbegrenzung, Pfadschutz, atomisches Speichern, gleichursprÃ¼ngliche API-Aufrufe, LÃ¶schen, manuellen Start und Stopp, Bildrotation, QR-Ansicht sowie EXIF-Datum/GPS und Dateidatum-RÃ¼ckfall ab. Der Pi erkannte alle 42 Fotos: 24 Hochformate und 18 quadratische oder querformatige Bilder. Live geprÃ¼ft wurden eine Gruppe echter Hochformate sowie ein einzeln dargestelltes vollstÃ¤ndiges Quadrat-/Querformat. Installierte Dateien stimmen mit dem Staging Ã¼berein; Datenbank-Hash, Dienst und Healthcheck wurden geprÃ¼ft. Sicherung einschlieÃŸlich konsistenter SQLite-Datenbank und 42 Fotos: `private Sicherung auf dem Pi; vertraulicher Pfad hier nicht veröffentlicht`.

## Öffentliche Installation

Bei einem Kiosk über localhost die vom Handy erreichbare Adresse über
`CAMPERDISPLAY_PUBLIC_URL` konfigurieren; siehe `../deploy/DIETPI.md`.
Der frühere feste QR-Code ist durch eine installationsabhängige Erzeugung ersetzt.
