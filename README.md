# Passwörter – lokaler Passwort-Manager (PWA)

Ein privater Passwort-Manager, der komplett im Browser deines Handys läuft.
Alle Daten bleiben **verschlüsselt auf dem Gerät** (nichts wird hochgeladen).

## Sicherheit
- Verschlüsselung: AES-256-GCM
- Schlüssel aus Master-Passwort via PBKDF2-HMAC-SHA256 (310.000 Runden)
- Keine externen Scripts/CDNs – alles in einer Datei
- Kein Server, kein Cloud-Sync

## Auf dem Handy einrichten
1. Diese Dateien in ein GitHub-Repo laden und GitHub Pages aktivieren
   (Settings → Pages → Branch: main → /root).
2. Die Pages-URL auf dem Handy im Browser öffnen (HTTPS ist nötig – GitHub Pages liefert das).
3. Menü des Browsers → **"Zum Startbildschirm hinzufügen"**.
   Danach startet die App wie eine echte App, auch offline.
4. Beim ersten Start ein **Master-Passwort** festlegen.

## Wichtig
- Es gibt **kein "Passwort vergessen"**. Ohne Master-Passwort sind die Daten verloren.
- Regelmäßig **Backup** machen (Menü → Verschlüsseltes Backup) und die Datei sicher ablegen.
- Wenn du den Browser-Cache/Website-Daten löschst, sind die lokal gespeicherten Passwörter weg – nur das Backup rettet dich dann.

## Dateien
- `index.html` – die komplette App
- `manifest.webmanifest`, `sw.js`, `icon-192.png`, `icon-512.png` – für Installierbarkeit & Offline
