"""
import_bitwarden.py - Importiert einen Bitwarden JSON-Export in den Vault.

Unterstützt unverschlüsselte Bitwarden-Exports (Einstellungen -> Export Vault
-> .json, NICHT "Encrypted JSON"). Items vom Typ "Login" (type == 1) werden
vollständig importiert, andere Typen (Notiz, Karte, Identität) werden als
Eintrag mit Notizfeld angelegt, damit nichts verloren geht.
"""

import json

TYPE_LOGIN = 1
TYPE_NOTE = 2
TYPE_CARD = 3
TYPE_IDENTITY = 4


def import_file(vault, filepath: str) -> dict:
    """Importiert Items aus einer Bitwarden-Export-Datei in den gegebenen Vault.

    Gibt eine Statistik zurück: {"imported": N, "skipped": N, "total": N}
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("encrypted"):
        raise ValueError(
            "Diese Datei ist ein verschlüsselter Bitwarden-Export. "
            "Bitte in Bitwarden 'Export Vault' -> Format 'JSON' (nicht "
            "'Encrypted JSON') wählen und erneut exportieren."
        )

    # Ordnernamen nachschlagen (id -> name)
    folder_lookup = {f["id"]: f["name"] for f in data.get("folders", [])}

    items = data.get("items", [])
    imported = 0
    skipped = 0

    for item in items:
        if item.get("deletedDate"):
            skipped += 1
            continue

        folder_name = folder_lookup.get(item.get("folderId"))
        folder_id = vault.get_or_create_folder(folder_name)
        name = item.get("name") or "(ohne Namen)"
        notes = item.get("notes") or ""

        item_type = item.get("type")

        if item_type == TYPE_LOGIN:
            login = item.get("login", {}) or {}
            username = login.get("username")
            password = login.get("password")
            uris = login.get("uris") or []
            url = uris[0]["uri"] if uris and uris[0].get("uri") else None
            totp = login.get("totp")
            vault.add_entry(
                name=name, username=username, password=password,
                url=url, notes=notes, totp=totp, folder_id=folder_id,
            )
            imported += 1

        elif item_type == TYPE_CARD:
            card = item.get("card", {}) or {}
            card_notes = (
                f"[Karte] Inhaber: {card.get('cardholderName', '')}, "
                f"Nummer: {card.get('number', '')}, "
                f"Ablauf: {card.get('expMonth', '')}/{card.get('expYear', '')}, "
                f"CVV: {card.get('code', '')}\n{notes}"
            )
            vault.add_entry(
                name=name, username=None, password=None,
                url=None, notes=card_notes, folder_id=folder_id,
            )
            imported += 1

        elif item_type == TYPE_IDENTITY:
            vault.add_entry(
                name=name, username=None, password=None,
                url=None, notes=f"[Identität]\n{notes}", folder_id=folder_id,
            )
            imported += 1

        elif item_type == TYPE_NOTE:
            vault.add_entry(
                name=name, username=None, password=None,
                url=None, notes=notes, folder_id=folder_id,
            )
            imported += 1

        else:
            skipped += 1

    return {"imported": imported, "skipped": skipped, "total": len(items)}
