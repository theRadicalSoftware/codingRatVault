from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .crypto import (
    KDF_NAME,
    KdfParams,
    VaultCrypto,
    access_id_hash,
    custom_field_aad,
    entry_aad,
    make_verification_token,
    verify_token,
)
from .models import CredentialEntry, VaultSummary
from .paths import ensure_private_parent


SCHEMA_VERSION = 1
DEFAULT_FOLDERS = ("Development", "Infrastructure", "Creative", "Personal", "Finance", "Imported")
DEFAULT_ENTRY_TYPES = (
    "Login",
    "API Key",
    "Server",
    "Database",
    "SSH Key",
    "Credit Card",
    "Secure Note",
    "AWS Account",
    "Environment Variables",
)
DEFAULT_SETTINGS = {
    "auto_lock_minutes": "10",
    "clipboard_clear_seconds": "30",
    "mask_usernames": "false",
    "travel_mode_active": "false",
    "travel_mode_backup_path": "",
    "travel_mode_removed_count": "0",
    "self_destruct_enabled": "false",
    "self_destruct_failed_attempts": "5",
    "failed_unlock_attempts": "0",
}


class VaultDatabase:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path).expanduser().resolve()
        ensure_private_parent(self.db_path)
        self._conn: sqlite3.Connection | None = None
        self.initialize_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
        return self._conn

    @contextmanager
    def transaction(self):
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def initialize_schema(self) -> None:
        with self.transaction() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL
                );

                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS folders (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    parent_id INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS entry_types (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    icon TEXT,
                    template TEXT
                );

                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY,
                    uid TEXT UNIQUE NOT NULL,
                    service BLOB NOT NULL,
                    account BLOB NOT NULL,
                    username BLOB NOT NULL,
                    password BLOB NOT NULL,
                    url BLOB NOT NULL,
                    notes BLOB NOT NULL,
                    folder_id INTEGER,
                    entry_type_id INTEGER,
                    favorite INTEGER NOT NULL DEFAULT 0,
                    health TEXT NOT NULL DEFAULT 'Strong',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL,
                    FOREIGN KEY (entry_type_id) REFERENCES entry_types(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS custom_fields (
                    id INTEGER PRIMARY KEY,
                    uid TEXT UNIQUE NOT NULL,
                    entry_id INTEGER NOT NULL,
                    name BLOB NOT NULL,
                    value BLOB NOT NULL,
                    field_type TEXT NOT NULL DEFAULT 'text',
                    is_sensitive INTEGER NOT NULL DEFAULT 1,
                    display_order INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY,
                    action TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_entries_folder_id ON entries(folder_id);
                CREATE INDEX IF NOT EXISTS idx_custom_fields_entry_id ON custom_fields(entry_id);
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, now_iso()),
            )
            self._ensure_defaults(conn)

    def _ensure_defaults(self, conn: sqlite3.Connection) -> None:
        for name in DEFAULT_FOLDERS:
            conn.execute(
                "INSERT OR IGNORE INTO folders (name, created_at) VALUES (?, ?)",
                (name, now_iso()),
            )
        for index, name in enumerate(DEFAULT_ENTRY_TYPES, start=1):
            conn.execute(
                "INSERT OR IGNORE INTO entry_types (id, name, icon, template) VALUES (?, ?, ?, ?)",
                (index, name, name.lower().replace(" ", "-"), ""),
            )
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value.encode("utf-8")))

    def vault_initialized(self) -> bool:
        return self.get_setting("verification_token") is not None

    def initialize_new_vault(self, access_id: str, crypto: VaultCrypto, params: KdfParams) -> None:
        if self.vault_initialized():
            raise RuntimeError("A vault already exists at this location")
        access_hash = access_id_hash(access_id, params.salt)
        with self.transaction() as conn:
            self.set_setting("schema_version", str(SCHEMA_VERSION), conn)
            self.set_setting("kdf_name", params.name, conn)
            self.set_setting("kdf_iterations", str(params.iterations), conn)
            self.set_setting("kdf_salt", params.salt, conn)
            self.set_setting("access_id_hash", access_hash, conn)
            self.set_setting("verification_token", make_verification_token(crypto), conn)
            self.set_setting("cipher", "aes-256-gcm", conn)
            self.set_setting("created_at", now_iso(), conn)
            self.log_activity("CREATE_VAULT", "Initialized encrypted Rat Mode vault", conn)

    def unlock(self, access_id: str, master_password: str) -> VaultCrypto:
        params = self.kdf_params()
        expected_access_hash = self.get_setting_text("access_id_hash")
        if expected_access_hash != access_id_hash(access_id, params.salt):
            raise ValueError("Access ID or passphrase did not match this vault")
        crypto = VaultCrypto.from_password(master_password, params)
        token = self.get_setting("verification_token")
        if not token or not verify_token(crypto, token):
            raise ValueError("Access ID or passphrase did not match this vault")
        self.log_activity("UNLOCK", "Vault unlocked")
        return crypto

    def kdf_params(self) -> KdfParams:
        salt = self.get_setting("kdf_salt")
        iterations = int(self.get_setting_text("kdf_iterations") or "0")
        name = self.get_setting_text("kdf_name") or KDF_NAME
        if not salt or iterations <= 0:
            raise ValueError("Vault is missing key derivation metadata")
        return KdfParams(salt=salt, iterations=iterations, name=name)

    def set_setting(self, key: str, value: str | bytes, conn: sqlite3.Connection | None = None) -> None:
        target = conn or self.conn
        blob = value if isinstance(value, bytes) else value.encode("utf-8")
        target.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, blob))
        if conn is None:
            target.commit()

    def get_setting(self, key: str) -> bytes | None:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return bytes(row["value"]) if row else None

    def get_setting_text(self, key: str) -> str | None:
        value = self.get_setting(key)
        return value.decode("utf-8") if value is not None else None

    def get_setting_bool(self, key: str, default: bool = False) -> bool:
        value = self.get_setting_text(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def get_setting_int(self, key: str, default: int = 0) -> int:
        value = self.get_setting_text(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def add_entry(self, entry: CredentialEntry, crypto: VaultCrypto) -> int:
        uid = uuid.uuid4().hex
        folder_id = self.folder_id(entry.folder)
        entry_type_id = self.entry_type_id(entry.entry_type)
        timestamp = now_iso()
        encrypted = {
            "service": crypto.encrypt_text(entry.service, entry_aad(uid, "service")),
            "account": crypto.encrypt_text(entry.account, entry_aad(uid, "account")),
            "username": crypto.encrypt_text(entry.username, entry_aad(uid, "username")),
            "password": crypto.encrypt_text(entry.password, entry_aad(uid, "password")),
            "url": crypto.encrypt_text(entry.url, entry_aad(uid, "url")),
            "notes": crypto.encrypt_text(entry.notes, entry_aad(uid, "notes")),
        }

        with self.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO entries
                    (uid, service, account, username, password, url, notes, folder_id,
                     entry_type_id, favorite, health, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    encrypted["service"],
                    encrypted["account"],
                    encrypted["username"],
                    encrypted["password"],
                    encrypted["url"],
                    encrypted["notes"],
                    folder_id,
                    entry_type_id,
                    1 if entry.favorite else 0,
                    entry.health,
                    timestamp,
                    timestamp,
                ),
            )
            entry_id = int(cursor.lastrowid)
            self._save_custom_fields(conn, entry_id, uid, entry.custom_fields, crypto)
            self.log_activity("CREATE_ENTRY", f"Created entry in {entry.folder}", conn)
        return entry_id

    def update_entry(self, entry_id: int, entry: CredentialEntry, crypto: VaultCrypto) -> None:
        row = self.conn.execute("SELECT uid FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if row is None:
            raise ValueError("Entry not found")

        uid = str(row["uid"])
        folder_id = self.folder_id(entry.folder)
        entry_type_id = self.entry_type_id(entry.entry_type)
        timestamp = now_iso()
        encrypted = {
            "service": crypto.encrypt_text(entry.service, entry_aad(uid, "service")),
            "account": crypto.encrypt_text(entry.account, entry_aad(uid, "account")),
            "username": crypto.encrypt_text(entry.username, entry_aad(uid, "username")),
            "password": crypto.encrypt_text(entry.password, entry_aad(uid, "password")),
            "url": crypto.encrypt_text(entry.url, entry_aad(uid, "url")),
            "notes": crypto.encrypt_text(entry.notes, entry_aad(uid, "notes")),
        }

        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE entries
                SET service = ?, account = ?, username = ?, password = ?, url = ?,
                    notes = ?, folder_id = ?, entry_type_id = ?, favorite = ?,
                    health = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    encrypted["service"],
                    encrypted["account"],
                    encrypted["username"],
                    encrypted["password"],
                    encrypted["url"],
                    encrypted["notes"],
                    folder_id,
                    entry_type_id,
                    1 if entry.favorite else 0,
                    entry.health,
                    timestamp,
                    entry_id,
                ),
            )
            conn.execute("DELETE FROM custom_fields WHERE entry_id = ?", (entry_id,))
            self._save_custom_fields(conn, entry_id, uid, entry.custom_fields, crypto)
            self.log_activity("UPDATE_ENTRY", f"Updated entry in {entry.folder}", conn)

    def delete_entry(self, entry_id: int) -> None:
        with self.transaction() as conn:
            cursor = conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            if cursor.rowcount == 0:
                raise ValueError("Entry not found")
            self.log_activity("DELETE_ENTRY", "Deleted credential entry", conn)

    def delete_non_travel_safe_entries(self) -> int:
        with self.transaction() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM entries WHERE favorite = 0").fetchone()
            removed = int(row["count"]) if row else 0
            conn.execute("DELETE FROM entries WHERE favorite = 0")
            self.log_activity("TRAVEL_MODE", f"Removed {removed} non-travel-safe entries", conn)
        return removed

    def count_entries(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS count FROM entries").fetchone()
        return int(row["count"]) if row else 0

    def count_travel_safe_entries(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS count FROM entries WHERE favorite = 1").fetchone()
        return int(row["count"]) if row else 0

    def import_entries(self, entries: Iterable[CredentialEntry], crypto: VaultCrypto) -> int:
        count = 0
        for entry in entries:
            if not entry.service or not entry.password:
                continue
            self.add_entry(entry, crypto)
            count += 1
        if count:
            self.log_activity("IMPORT", f"Imported {count} entries")
        return count

    def replace_entries(self, entries: Iterable[CredentialEntry], crypto: VaultCrypto) -> int:
        with self.transaction() as conn:
            conn.execute("DELETE FROM custom_fields")
            conn.execute("DELETE FROM entries")
            self.log_activity("RESTORE_CLEAR", "Cleared vault entries before restore", conn)
        count = self.import_entries(entries, crypto)
        self.log_activity("RESTORE", f"Restored {count} entries from backup")
        return count

    def list_entries(self, crypto: VaultCrypto) -> list[CredentialEntry]:
        rows = self.conn.execute(
            """
            SELECT e.*, f.name AS folder_name, t.name AS entry_type_name
            FROM entries e
            LEFT JOIN folders f ON f.id = e.folder_id
            LEFT JOIN entry_types t ON t.id = e.entry_type_id
            ORDER BY e.updated_at DESC, e.id DESC
            """
        ).fetchall()
        return [self._entry_from_row(row, crypto) for row in rows]

    def _entry_from_row(self, row: sqlite3.Row, crypto: VaultCrypto) -> CredentialEntry:
        uid = row["uid"]
        custom_fields = self._load_custom_fields(row["id"], uid, crypto)
        updated = row["updated_at"].split("T", 1)[0]
        return CredentialEntry(
            id=int(row["id"]),
            service=crypto.decrypt_text(row["service"], entry_aad(uid, "service")),
            account=crypto.decrypt_text(row["account"], entry_aad(uid, "account")),
            username=crypto.decrypt_text(row["username"], entry_aad(uid, "username")),
            password=crypto.decrypt_text(row["password"], entry_aad(uid, "password")),
            url=crypto.decrypt_text(row["url"], entry_aad(uid, "url")),
            folder=row["folder_name"] or "Imported",
            entry_type=row["entry_type_name"] or "Login",
            notes=crypto.decrypt_text(row["notes"], entry_aad(uid, "notes")),
            health=row["health"],
            updated=updated,
            favorite=bool(row["favorite"]),
            custom_fields=custom_fields,
        )

    def _save_custom_fields(
        self,
        conn: sqlite3.Connection,
        entry_id: int,
        entry_uid: str,
        fields: dict[str, str],
        crypto: VaultCrypto,
    ) -> None:
        for index, (name, value) in enumerate(fields.items()):
            field_uid = uuid.uuid4().hex
            conn.execute(
                """
                INSERT INTO custom_fields (uid, entry_id, name, value, display_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    field_uid,
                    entry_id,
                    crypto.encrypt_text(name, custom_field_aad(entry_uid, field_uid, "name")),
                    crypto.encrypt_text(value, custom_field_aad(entry_uid, field_uid, "value")),
                    index,
                ),
            )

    def _load_custom_fields(self, entry_id: int, entry_uid: str, crypto: VaultCrypto) -> dict[str, str]:
        rows = self.conn.execute(
            "SELECT uid, name, value FROM custom_fields WHERE entry_id = ? ORDER BY display_order, id",
            (entry_id,),
        ).fetchall()
        fields: dict[str, str] = {}
        for row in rows:
            field_uid = row["uid"]
            name = crypto.decrypt_text(row["name"], custom_field_aad(entry_uid, field_uid, "name"))
            value = crypto.decrypt_text(row["value"], custom_field_aad(entry_uid, field_uid, "value"))
            fields[name] = value
        return fields

    def folder_id(self, name: str) -> int:
        folder = (name or "Imported").strip() or "Imported"
        with self.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO folders (name, created_at) VALUES (?, ?)",
                (folder, now_iso()),
            )
            row = conn.execute("SELECT id FROM folders WHERE name = ?", (folder,)).fetchone()
        return int(row["id"])

    def add_folder(self, name: str) -> int:
        folder = (name or "").strip()
        if not folder:
            raise ValueError("Folder name is required")
        with self.transaction() as conn:
            existing = conn.execute("SELECT id FROM folders WHERE name = ?", (folder,)).fetchone()
            if existing is not None:
                raise ValueError("Folder already exists")
            cursor = conn.execute(
                "INSERT INTO folders (name, created_at) VALUES (?, ?)",
                (folder, now_iso()),
            )
            self.log_activity("CREATE_FOLDER", f"Created folder {folder}", conn)
        return int(cursor.lastrowid)

    def rename_folder(self, old_name: str, new_name: str) -> None:
        old_folder = (old_name or "").strip()
        new_folder = (new_name or "").strip()
        if not old_folder or not new_folder:
            raise ValueError("Folder names are required")
        with self.transaction() as conn:
            existing = conn.execute("SELECT id FROM folders WHERE name = ?", (new_folder,)).fetchone()
            if existing is not None and new_folder != old_folder:
                raise ValueError("Folder already exists")
            cursor = conn.execute("UPDATE folders SET name = ? WHERE name = ?", (new_folder, old_folder))
            if cursor.rowcount == 0:
                raise ValueError("Folder not found")
            self.log_activity("RENAME_FOLDER", f"Renamed {old_folder} to {new_folder}", conn)

    def delete_folder(self, name: str) -> None:
        folder = (name or "").strip()
        if not folder:
            raise ValueError("Folder name is required")
        with self.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO folders (name, created_at) VALUES (?, ?)",
                ("Imported", now_iso()),
            )
            imported_row = conn.execute("SELECT id FROM folders WHERE name = ?", ("Imported",)).fetchone()
            imported_id = int(imported_row["id"])
            row = conn.execute("SELECT id FROM folders WHERE name = ?", (folder,)).fetchone()
            if row is None:
                raise ValueError("Folder not found")
            folder_id = int(row["id"])
            if folder_id == imported_id:
                raise ValueError("The Imported folder cannot be deleted")
            conn.execute("UPDATE entries SET folder_id = ? WHERE folder_id = ?", (imported_id, folder_id))
            conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            self.log_activity("DELETE_FOLDER", f"Deleted folder {folder}; moved entries to Imported", conn)

    def entry_type_id(self, name: str) -> int:
        entry_type = (name or "Login").strip() or "Login"
        with self.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO entry_types (name, icon, template) VALUES (?, ?, ?)",
                (entry_type, entry_type.lower().replace(" ", "-"), ""),
            )
            row = conn.execute("SELECT id FROM entry_types WHERE name = ?", (entry_type,)).fetchone()
        return int(row["id"])

    def folder_names(self) -> list[str]:
        rows = self.conn.execute("SELECT name FROM folders ORDER BY name").fetchall()
        return [str(row["name"]) for row in rows]

    def entry_type_names(self) -> list[str]:
        rows = self.conn.execute("SELECT name FROM entry_types ORDER BY id, name").fetchall()
        return [str(row["name"]) for row in rows]

    def is_travel_mode_active(self) -> bool:
        return self.get_setting_bool("travel_mode_active", False)

    def set_travel_mode_state(self, active: bool, backup_path: str = "", removed_count: int = 0) -> None:
        with self.transaction() as conn:
            self.set_setting("travel_mode_active", "true" if active else "false", conn)
            self.set_setting("travel_mode_backup_path", backup_path, conn)
            self.set_setting("travel_mode_removed_count", str(removed_count), conn)
            self.log_activity("TRAVEL_MODE", "Travel mode activated" if active else "Travel mode deactivated", conn)

    def register_failed_unlock(self) -> bool:
        attempts = self.get_setting_int("failed_unlock_attempts", 0) + 1
        threshold = self.get_setting_int("self_destruct_failed_attempts", 5)
        enabled = self.get_setting_bool("self_destruct_enabled", False)
        with self.transaction() as conn:
            self.set_setting("failed_unlock_attempts", str(attempts), conn)
            self.log_activity("UNLOCK_FAILED", f"Failed unlock attempt {attempts}", conn)
        return enabled and threshold > 0 and attempts >= threshold

    def reset_failed_unlocks(self) -> None:
        self.set_setting("failed_unlock_attempts", "0")

    def self_destruct(self, secure: bool = True) -> tuple[bool, str]:
        try:
            self.log_activity("SELF_DESTRUCT", "Self-destruct initiated")
        except Exception:
            pass

        targets = [
            self.db_path,
            Path(f"{self.db_path}-wal"),
            Path(f"{self.db_path}-shm"),
        ]
        self.close()

        try:
            for target in targets:
                if not target.exists():
                    continue
                if secure:
                    try:
                        size = target.stat().st_size
                        with target.open("r+b") as handle:
                            handle.write(b"\0" * size)
                            handle.flush()
                            os.fsync(handle.fileno())
                    except OSError:
                        pass
                target.unlink(missing_ok=True)
            return True, "Vault database destroyed"
        except Exception as exc:
            return False, f"Self-destruct failed: {exc}"

    def summary(self, crypto: VaultCrypto) -> VaultSummary:
        entries = self.list_entries(crypto)
        return VaultSummary(
            entries=len(entries),
            folders=len({entry.folder for entry in entries}),
            weak_entries=len([entry for entry in entries if entry.health == "Weak"]),
            storage_label="Encrypted SQLite",
            database_path=str(self.db_path),
        )

    def log_activity(
        self,
        action: str,
        description: str,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        target = conn or self.conn
        target.execute(
            "INSERT INTO activity_log (action, description, created_at) VALUES (?, ?, ?)",
            (action, description, now_iso()),
        )
        if conn is None:
            target.commit()

    def recent_activity(self, limit: int = 8) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT action, description, created_at FROM activity_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()
