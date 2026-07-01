from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.crypto import VaultCrypto
from app.core.database import VaultDatabase
from app.core.import_export import load_entries_from_path, write_export_file
from app.core.models import CredentialEntry, VaultSummary
from app.core.paths import default_vault_db_path
from app.core.security.breach import BreachMonitor


class VaultController:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path).expanduser().resolve() if db_path else default_vault_db_path()
        self.db = VaultDatabase(self.db_path)
        self.crypto: VaultCrypto | None = None
        self.access_id = ""
        self.breach_monitor = BreachMonitor()

    @property
    def unlocked(self) -> bool:
        return self.crypto is not None

    def vault_exists(self) -> bool:
        return self.db.vault_initialized()

    def create_vault(self, access_id: str, master_password: str) -> str:
        crypto, params = VaultCrypto.create(master_password)
        self.db.initialize_new_vault(access_id, crypto, params)
        self.crypto = crypto
        self.access_id = access_id
        return f"Encrypted Rat Mode vault created at {self.db_path}."

    def unlock_vault(self, access_id: str, master_password: str) -> str:
        self.crypto = self.db.unlock(access_id, master_password)
        self.access_id = access_id
        self.db.reset_failed_unlocks()
        return f"Encrypted vault unlocked for {access_id}."

    def lock(self) -> None:
        self.crypto = None
        self.access_id = ""
        self.db.log_activity("LOCK", "Vault locked")

    def list_entries(self) -> list[CredentialEntry]:
        self._require_unlocked()
        return self.db.list_entries(self.crypto)

    def add_entry(self, entry: CredentialEntry) -> int:
        self._require_unlocked()
        return self.db.add_entry(entry, self.crypto)

    def update_entry(self, entry_id: int, entry: CredentialEntry) -> None:
        self._require_unlocked()
        self.db.update_entry(entry_id, entry, self.crypto)

    def delete_entry(self, entry_id: int) -> None:
        self._require_unlocked()
        self.db.delete_entry(entry_id)

    def import_path(self, path: Path | str, passphrase: str | None = None) -> int:
        self._require_unlocked()
        entries = load_entries_from_path(path, passphrase=passphrase)
        return self.db.import_entries(entries, self.crypto)

    def restore_path(self, path: Path | str, passphrase: str | None = None) -> int:
        self._require_unlocked()
        entries = load_entries_from_path(path, passphrase=passphrase)
        return self.db.replace_entries(entries, self.crypto)

    def export_path(self, path: Path | str, passphrase: str) -> int:
        entries = self.list_entries()
        write_export_file(path, entries, passphrase)
        self.db.log_activity("EXPORT", f"Exported {len(entries)} entries")
        return len(entries)

    def activate_travel_mode(self, backup_path: Path | str, passphrase: str) -> dict[str, int]:
        self._require_unlocked()
        entries = self.list_entries()
        write_export_file(backup_path, entries, passphrase)
        safe_count = self.db.count_travel_safe_entries()
        removed_count = self.db.delete_non_travel_safe_entries()
        self.db.set_travel_mode_state(True, str(Path(backup_path).expanduser()), removed_count)
        return {"total": len(entries), "kept": safe_count, "removed": removed_count}

    def deactivate_travel_mode(self, backup_path: Path | str, passphrase: str) -> int:
        count = self.restore_path(backup_path, passphrase)
        self.db.set_travel_mode_state(False, "", 0)
        return count

    def folders(self) -> list[str]:
        return self.db.folder_names()

    def add_folder(self, name: str) -> int:
        self._require_unlocked()
        return self.db.add_folder(name)

    def rename_folder(self, old_name: str, new_name: str) -> None:
        self._require_unlocked()
        self.db.rename_folder(old_name, new_name)

    def delete_folder(self, name: str) -> None:
        self._require_unlocked()
        self.db.delete_folder(name)

    def entry_types(self) -> list[str]:
        return self.db.entry_type_names()

    def summary(self) -> VaultSummary:
        self._require_unlocked()
        return self.db.summary(self.crypto)

    def recent_activity(self) -> list[dict]:
        return self.db.recent_activity()

    def setting(self, key: str, default: str = "") -> str:
        return self.db.get_setting_text(key) or default

    def setting_bool(self, key: str, default: bool = False) -> bool:
        return self.db.get_setting_bool(key, default)

    def setting_int(self, key: str, default: int = 0) -> int:
        return self.db.get_setting_int(key, default)

    def set_setting(self, key: str, value: str | int | bool) -> None:
        if isinstance(value, bool):
            stored = "true" if value else "false"
        else:
            stored = str(value)
        self.db.set_setting(key, stored)
        self.db.log_activity("SETTINGS", f"Updated {key}")

    def is_travel_mode_active(self) -> bool:
        return self.db.is_travel_mode_active()

    def travel_mode_backup_path(self) -> str:
        return self.setting("travel_mode_backup_path")

    def register_failed_unlock(self) -> bool:
        return self.db.register_failed_unlock()

    def self_destruct(self) -> tuple[bool, str]:
        self.crypto = None
        self.access_id = ""
        return self.db.self_destruct()

    def password_health_report(self) -> dict[str, Any]:
        entries = self.list_entries()
        password_counts: dict[str, int] = {}
        for entry in entries:
            password_counts[entry.password] = password_counts.get(entry.password, 0) + 1

        rows: list[dict[str, str]] = []
        strong = 0
        review = 0
        weak = 0
        reused = 0

        for entry in entries:
            issues: list[str] = []
            score = password_score(entry.password)
            if score < 3:
                issues.append("weak password")
            if password_counts.get(entry.password, 0) > 1:
                issues.append("reused password")
                reused += 1
            if not entry.username:
                issues.append("missing username")
            if entry.entry_type != "Secure Note" and not entry.url:
                issues.append("missing URL")

            if score >= 4 and not issues:
                status = "Strong"
                strong += 1
            elif score < 3:
                status = "Weak"
                weak += 1
            else:
                status = "Review"
                review += 1

            rows.append(
                {
                    "service": entry.service,
                    "folder": entry.folder,
                    "status": status,
                    "issues": ", ".join(issues) if issues else "clear",
                }
            )

        return {
            "total": len(entries),
            "strong": strong,
            "review": review,
            "weak": weak,
            "reused": reused,
            "rows": rows,
        }

    def breach_summary(self) -> str:
        entries = self.list_entries()
        if not entries:
            return "No credentials to check"
        checked = 0
        compromised = 0
        for entry in entries[:10]:
            result = self.breach_monitor.check_password(entry.password)
            if result.checked:
                checked += 1
                if result.count:
                    compromised += 1
        if checked == 0:
            return "Breach service unavailable"
        if compromised:
            return f"{compromised} exposed passwords found"
        return f"{checked} passwords clear"

    def _require_unlocked(self) -> None:
        if self.crypto is None:
            raise RuntimeError("Vault is locked")


def password_score(password: str) -> int:
    score = 0
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    if any(char.islower() for char in password) and any(char.isupper() for char in password):
        score += 1
    if any(char.isdigit() for char in password):
        score += 1
    if any(not char.isalnum() for char in password):
        score += 1
    return score
