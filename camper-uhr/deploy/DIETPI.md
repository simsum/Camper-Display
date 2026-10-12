# Camper-Display auf DietPi

Diese Anleitung richtet sich an ein bereits eingerichtetes DietPi-System mit
Python 3.11 oder neuer (lokal getestet mit 3.12), Git und Chromium-Kiosk.
Display und Touch müssen unter Linux bereits funktionieren. Das Projekt wurde
auf einem Raspberry Pi 3 mit 1480 × 320 Pixeln entwickelt; andere Hardware
benötigt eigene Tests. Es gibt kein automatisches Systemupdate, Partitionsskript
oder zugesichertes fertiges Installations-Image.

## 1. Vorbereiten

Bestehende Installation und private Daten sichern. Bei einem vorhandenen System
zuerst Dienstbenutzer, Datenpfad, Display und Kiosk prüfen. Benötigte Systempakete
gezielt über DietPi installieren; ein laufendes Gerät nicht ungeprüft umbauen.

Ein möglicher Codepfad ist `/opt/camper-display`, mit dem eigentlichen Code
im Unterordner `camper-uhr`. Für eine neue Installation:

```sh
sudo git clone https://github.com/simsum/Camper-Display.git /opt/camper-display
cd /opt/camper-display/camper-uhr
sudo python3 -m venv venv
sudo venv/bin/python -m pip install -r requirements.txt
```

Die Befehle setzen bewusst ein neues Zielverzeichnis voraus. Eine bestehende
Installation nicht durch erneutes Klonen oder Kopieren überschreiben.

## 2. Backend und Daten

`camperdisplay.service` ist eine Vorlage mit dem Codepfad oben und dem
Datenverzeichnis `/var/lib/camperdisplay`. Sie verwendet wie die ursprüngliche
Hardwareinstallation root für Display-/Touch-Zugriffe. Ein eigener unprivilegierter
Dienstbenutzer ist möglich, benötigt aber passende Rechte für Daten und Geräte.
Die Vorlage nicht mit ungeprüften Pfaden übernehmen.

```sh
sudo install -d -m 0700 /var/lib/camperdisplay
sudo install -m 0644 deploy/camperdisplay.service /etc/systemd/system/camperdisplay.service
sudo systemctl daemon-reload
sudo systemctl enable --now camperdisplay.service
curl -fsS http://127.0.0.1:8080/api/health
```

Konfiguration im Browser unter `http://<PI-IP>:8080/settings`. Der Dienst bindet
für den Zugriff vom Handy an alle Schnittstellen. Die Anwendung hat keine
Benutzeranmeldung und darf nur im vertrauenswürdigen LAN erreichbar sein;
siehe [SECURITY.md](../../SECURITY.md).

## 3. Foto-QR-Code

Der Kiosk läuft häufig unter `http://localhost:8080`. Diese Adresse ist vom
Handy nicht erreichbar. Daher die stabile LAN-Adresse oder einen funktionierenden
LAN-DNS-Namen des Pis als systemd-Override setzen:

```sh
sudo systemctl edit camperdisplay.service
```

```ini
[Service]
Environment="CAMPERDISPLAY_PUBLIC_URL=http://camperdisplay.local:8080"
```

`camperdisplay.local` durch den tatsächlich vom Handy erreichbaren Namen oder
die feste LAN-IP ersetzen. Nur Ursprung mit Protokoll und Port angeben, keinen
Pfad und keine Zugangsdaten. Danach den Dienst neu starten. Der QR-Code wird
lokal erzeugt und verweist auf `/photos`; kein externer QR-Dienst wird verwendet.
Ohne erreichbare Adresse zeigt der Kiosk einen Einrichtungshinweis.

## 4. Kiosk und Touch

Chromium im DietPi-Kiosk auf `http://127.0.0.1:8080/` öffnen. Die Dateien
`dietpi-chromium-autostart.sh`, `camperdisplay-kiosk.service` und
`99-camperdisplay-touch.conf` sind Beispiele für unterschiedliche Startwege.
Nur einen Kiosk-Startweg aktivieren; den Dienst für Benutzer `pi` nicht
unverändert auf ein anders eingerichtetes DietPi übernehmen.

Physische Displayauflösung und Drehung über die eigene Linux-/DietPi-Konfiguration
setzen; die Touchmatrix muss dazu passen. Die feste App-Designfläche bleibt
1480 × 320 Pixel. Die 3D-Karte benötigt funktionierendes WebGL. Das alte
Kioskskript mit deaktivierter GPU wurde entsprechend berichtigt, muss aber
auf dem jeweiligen Grafiktreiber geprüft werden. Ein schreibgeschütztes Root-
Dateisystem und Partitionierungsänderungen sind ausdrücklich separate Vorhaben.

## 5. Prüfen

Health-Endpunkt, alle gewünschten Module, Stand/Fahrt, Touch und Nachtmodus prüfen.
GPS-Routeradresse, Kalender und Traccar individuell einrichten. Vom Handy die
Foto-Adresse öffnen, einen Test-Upload durchführen und den QR-Code scannen.
Einstellungen und Fotos separat sichern; siehe [BACKUP.md](../docs/BACKUP.md).
