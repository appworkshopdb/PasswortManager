"""
vault.py - Verschlüsselte SQLite-Datenbank für den Passwort-Manager.

Alle Passwörter werden mit einem aus dem Master-Passwort abgeleiteten
Schlüssel (PBKDF2-HMAC-SHA256 + Fernet/AES) verschlüsselt gespeichert.
Das Master-Passwort selbst wird NIE gespeichert.
"""

import sqlite3
import os
import base64
import time
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault.db")
PBKDF2_ITERATIONS = 480_000  # aktuell empfohlener Wert (OWASP 2023+)


def _derive_key(master_password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    key = kdf.derive(master_password.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


class WrongMasterPassword(Exception):
    pass


class Vault:
    """Kapselt Verbindung, Verschlüsselung und CRUD-Operationen."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._fernet: Fernet | None = None
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                salt BLOB NOT NULL,
                verifier BLOB NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id INTEGER,
                name TEXT NOT NULL,
                username TEXT,
                password_enc BLOB,
                url TEXT,
                notes_enc BLOB,
                totp_enc BLOB,
                created_at REAL,
                updated_at REAL,
                FOREIGN KEY (folder_id) REFERENCES folders(id)
            )
        """)
        self.conn.commit()

    # ---------- Master-Passwort / Setup ----------

    def is_initialized(self) -> bool:
        cur = self.conn.execute("SELECT 1 FROM meta WHERE id = 1")
        return cur.fetchone() is not None

    def setup_master_password(self, master_password: str):
        """Beim allerersten Start: legt Salt + Verifier an."""
        salt = os.urandom(16)
        key = _derive_key(master_password, salt)
        fernet = Fernet(key)
        verifier = fernet.encrypt(b"vault-ok")
        self.conn.execute(
            "INSERT INTO meta (id, salt, verifier) VALUES (1, ?, ?)",
            (salt, verifier),
        )
        self.conn.commit()
        self._fernet = fernet

    def unlock(self, master_password: str):
        """Bei jedem weiteren Start: prüft Master-Passwort und entsperrt."""
        row = self.conn.execute("SELECT salt, verifier FROM meta WHERE id = 1").fetchone()
        if row is None:
            raise RuntimeError("Vault ist noch nicht initialisiert.")
        salt, verifier = row["salt"], row["verifier"]
        key = _derive_key(master_password, salt)
        fernet = Fernet(key)
        try:
            fernet.decrypt(verifier)
        except InvalidToken:
            raise WrongMasterPassword("Master-Passwort ist falsch.")
        self._fernet = fernet

    def _enc(self, plaintext: str | None) -> bytes | None:
        if plaintext is None:
            return None
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def _dec(self, ciphertext: bytes | None) -> str | None:
        if ciphertext is None:
            return None
        return self._fernet.decrypt(ciphertext).decode("utf-8")

    # ---------- Folders ----------

    def get_or_create_folder(self, name: str | None) -> int | None:
        if not name:
            return None
        cur = self.conn.execute("SELECT id FROM folders WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute("INSERT INTO folders (name) VALUES (?)", (name,))
        self.conn.commit()
        return cur.lastrowid

    def list_folders(self):
        return self.conn.execute("SELECT id, name FROM folders ORDER BY name").fetchall()

    # ---------- Entries CRUD ----------

    def add_entry(self, name, username, password, url=None, notes=None, totp=None, folder_id=None):
        now = time.time()
        self.conn.execute(
            """INSERT INTO entries
               (folder_id, name, username, password_enc, url, notes_enc, totp_enc, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (folder_id, name, username, self._enc(password), url,
             self._enc(notes), self._enc(totp), now, now),
        )
        self.conn.commit()

    def update_entry(self, entry_id, name, username, password, url=None, notes=None, totp=None, folder_id=None):
        self.conn.execute(
            """UPDATE entries SET folder_id=?, name=?, username=?, password_enc=?,
               url=?, notes_enc=?, totp_enc=?, updated_at=? WHERE id=?""",
            (folder_id, name, username, self._enc(password), url,
             self._enc(notes), self._enc(totp), time.time(), entry_id),
        )
        self.conn.commit()

    def delete_entry(self, entry_id):
        self.conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self.conn.commit()

    def list_entries(self, search: str = ""):
        if search:
            like = f"%{search}%"
            rows = self.conn.execute(
                """SELECT * FROM entries WHERE name LIKE ? OR username LIKE ? OR url LIKE ?
                   ORDER BY name COLLATE NOCASE""",
                (like, like, like),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM entries ORDER BY name COLLATE NOCASE").fetchall()
        return rows

    def get_entry_decrypted(self, entry_id):
        row = self.conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "username": row["username"],
            "password": self._dec(row["password_enc"]),
            "url": row["url"],
            "notes": self._dec(row["notes_enc"]),
            "totp": self._dec(row["totp_enc"]),
            "folder_id": row["folder_id"],
        }

    def close(self):
        self.conn.close()
