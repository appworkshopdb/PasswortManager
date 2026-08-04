# Mein Passwort-Manager

Ein einfacher, lokaler Passwort-Manager für den privaten Gebrauch.
Alle Daten bleiben auf deinem Rechner (Datei `vault.db` im selben Ordner)
und sind mit deinem Master-Passwort verschlüsselt (AES via `cryptography`/Fernet,
Schlüsselableitung mit PBKDF2-HMAC-SHA256, 480.000 Runden).

## Als eigenes GitHub-Repo aufsetzen

```bash
cd password-manager
git init
git add .
git commit -m "Initial commit: lokaler Passwort-Manager"
git branch -M main
git remote add origin https://github.com/<dein-username>/<repo-name>.git
git push -u origin main
```

Die `.gitignore` sorgt dafür, dass `vault.db` (deine verschlüsselten Passwörter)
und eventuelle Bitwarden-Export-Dateien **niemals** mit committet werden.
Falls du aus Versehen doch mal eine `vault.db` oder Export-Datei committest:
Nicht einfach löschen, sondern die Git-Historie bereinigen (z. B. mit
`git filter-repo` oder `BFG Repo-Cleaner`) und danach das Master-Passwort
sowie alle betroffenen Zugangsdaten ändern.

## Installation

```bash
pip install -r requirements.txt
```

Tkinter ist bei den meisten Python-Installationen bereits dabei. Falls nicht
(unter Linux manchmal separat nötig):

```bash
sudo apt install python3-tk
```

## Start

```bash
python3 main.py
```

Beim allerersten Start legst du ein Master-Passwort fest. **Merk es dir gut –
es gibt keine "Passwort vergessen"-Funktion.** Ohne Master-Passwort sind die
gespeicherten Daten nicht wiederherstellbar (das ist Absicht, so funktioniert
auch Bitwarden & Co.).

## Bitwarden-Import

1. In Bitwarden: Einstellungen → "Export Vault" → Format **"JSON"** wählen
   (NICHT "Encrypted JSON" – das kann dieses Tool nicht lesen).
2. In diesem Tool: Menü **Datei → Aus Bitwarden importieren...**
3. Die exportierte `.json`-Datei auswählen.

⚠️ Der unverschlüsselte Bitwarden-Export enthält alle deine Passwörter im
Klartext. Lösche die Export-Datei nach dem Import sofort und sicher
(z. B. mit `shred` unter Linux), da sie sonst ein Sicherheitsrisiko darstellt.

## Funktionen

- Einträge anlegen, bearbeiten, löschen
- Suche über Name / Benutzername / URL
- Passwort anzeigen/verstecken, in Zwischenablage kopieren
- Zufälliges, sicheres Passwort generieren (16 Zeichen)
- Import aus Bitwarden-JSON-Export (Logins, Notizen, Karten, Identitäten)
- Ordner werden aus Bitwarden übernommen

## Bekannte Grenzen (bewusst einfach gehalten)

- Keine Cloud-Synchronisierung, kein Multi-Device-Zugriff
- Keine 2FA/TOTP-Code-Generierung (TOTP-Secrets werden aber importiert und
  in den Notizen mitgespeichert)
- Kein automatisches Backup – sichere `vault.db` selbst regelmäßig
  (z. B. verschlüsselt in eine Cloud kopieren)
- Kein Passwort-Reset: bei vergessenem Master-Passwort sind die Daten weg

## Dateien

- `main.py` – Programmstart & grafische Oberfläche (Tkinter)
- `vault.py` – Verschlüsselung & Datenbank-Logik
- `import_bitwarden.py` – Bitwarden-Import
- `vault.db` – wird beim ersten Start automatisch angelegt (deine Daten)
