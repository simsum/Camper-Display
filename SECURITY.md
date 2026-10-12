# Betrieb und private Daten

Camper-Display ist für ein vertrauenswürdiges Camper-LAN vorgesehen.
Einstellungen, Fotoverwaltung und API besitzen keine Benutzeranmeldung.
Den HTTP-Port nicht direkt ins Internet freigeben. Für Fernzugriff einen
angemessen abgesicherten VPN-Zugang verwenden.

Kalender-Freigabelinks und Traccar-Token gehören ausschließlich in die lokale
Konfiguration. Private Datenbanken, Fotos, Standortdaten, Protokolle und
Sicherungen dürfen nicht in Git aufgenommen werden. Die `.gitignore` enthält
entsprechende Ausschlüsse; `git add -f` umgeht diese bewusst.

GPS-basierte Funktionen können Koordinaten an Open-Meteo und
Nominatim/OpenStreetMap senden. Die Ankunftsanzeige fragt zusätzlich Wikipedia
und Wikimedia ab. Der Foto-Upload löst vorhandene EXIF-GPS-Daten zu einem Ortsnamen
auf. Wer das nicht möchte, entfernt Standortmetadaten vor dem Upload.

Geheimnisse oder reale Bewegungsdaten bitte nicht in öffentlichen Issues posten.
Eine Sicherheitsmeldung zunächst ohne sensible Details beim Projektinhaber
ankündigen und einen privaten Übertragungsweg abstimmen. Vor dem Veröffentlichen
von Logs und Screenshots personenbezogene Angaben prüfen.
