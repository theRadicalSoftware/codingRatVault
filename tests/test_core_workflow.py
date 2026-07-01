from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.core.paths import default_vault_db_path, demo_vault_db_path
from app.core.models import CredentialEntry
from app.gui.controllers.vault_controller import VaultController


class CoreWorkflowTest(unittest.TestCase):
    def test_create_add_lock_unlock_and_encrypt_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "rat.sqlite3"
            controller = VaultController(db_path)
            controller.create_vault("rat@example.local", "correct horse battery staple")
            controller.add_entry(
                CredentialEntry(
                    service="Example Service",
                    account="Workspace",
                    username="rat@example.local",
                    password="S3cret!234567890",
                    url="https://example.test",
                    folder="Development",
                    entry_type="Login",
                    notes="sensitive note",
                )
            )

            entries = controller.list_entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].service, "Example Service")
            self.assertEqual(entries[0].notes, "sensitive note")

            raw = sqlite3.connect(db_path).execute("SELECT service, notes FROM entries").fetchone()
            self.assertNotIn(b"Example Service", raw[0])
            self.assertNotIn(b"sensitive note", raw[1])

            controller.lock()
            controller.unlock_vault("rat@example.local", "correct horse battery staple")
            self.assertEqual(controller.list_entries()[0].username, "rat@example.local")

    def test_export_and_import_with_passphrase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            export_path = tmp_path / "backup.ratvault"
            source = VaultController(tmp_path / "source.sqlite3")
            source.create_vault("source@example.local", "correct horse battery staple")
            source.add_entry(
                CredentialEntry(
                    service="Portable Record",
                    account="Workspace",
                    username="user",
                    password="Portable!234567890",
                    url="https://portable.test",
                    folder="Imported",
                    entry_type="Login",
                    notes="moves through encrypted export",
                )
            )

            self.assertEqual(source.export_path(export_path, "export passphrase"), 1)
            package = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertEqual(package["format"], "coding-rat-vault-export")
            self.assertTrue(package["encrypted"])

            target = VaultController(tmp_path / "target.sqlite3")
            target.create_vault("target@example.local", "another correct battery staple")
            self.assertEqual(target.import_path(export_path, "export passphrase"), 1)
            self.assertEqual(target.list_entries()[0].service, "Portable Record")

    def test_update_delete_and_custom_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "rat.sqlite3"
            controller = VaultController(db_path)
            controller.create_vault("rat@example.local", "correct horse battery staple")
            entry_id = controller.add_entry(
                CredentialEntry(
                    service="Original",
                    account="Workspace",
                    username="rat",
                    password="Original!234567890",
                    url="https://original.test",
                    folder="Development",
                    entry_type="Login",
                    notes="original note",
                    custom_fields={"api token": "token-value"},
                )
            )

            controller.update_entry(
                entry_id,
                CredentialEntry(
                    service="Updated",
                    account="Workspace",
                    username="rat",
                    password="Updated!234567890",
                    url="https://updated.test",
                    folder="Creative",
                    entry_type="API Key",
                    notes="updated note",
                    custom_fields={"rotation": "quarterly"},
                ),
            )
            updated = controller.list_entries()[0]
            self.assertEqual(updated.service, "Updated")
            self.assertEqual(updated.folder, "Creative")
            self.assertEqual(updated.custom_fields, {"rotation": "quarterly"})

            raw = sqlite3.connect(db_path).execute(
                "SELECT service, notes FROM entries WHERE id = ?",
                (entry_id,),
            ).fetchone()
            self.assertNotIn(b"Updated", raw[0])
            self.assertNotIn(b"updated note", raw[1])

            controller.delete_entry(entry_id)
            self.assertEqual(controller.list_entries(), [])

    def test_folder_add_rename_delete_moves_entries_to_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "rat.sqlite3"
            controller = VaultController(db_path)
            controller.create_vault("rat@example.local", "correct horse battery staple")
            controller.add_folder("Clients")
            entry_id = controller.add_entry(
                CredentialEntry(
                    service="Client Portal",
                    account="Client",
                    username="rat",
                    password="Client!234567890",
                    url="https://client.test",
                    folder="Clients",
                    entry_type="Login",
                    notes="client record",
                )
            )

            controller.rename_folder("Clients", "Client Work")
            self.assertEqual(controller.list_entries()[0].folder, "Client Work")

            controller.delete_folder("Client Work")
            entry = controller.list_entries()[0]
            self.assertEqual(entry.id, entry_id)
            self.assertEqual(entry.folder, "Imported")

    def test_restore_replaces_existing_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            backup_path = tmp_path / "restore.ratvault"
            source = VaultController(tmp_path / "source.sqlite3")
            source.create_vault("source@example.local", "correct horse battery staple")
            source.add_entry(
                CredentialEntry(
                    service="Backup Entry",
                    account="Workspace",
                    username="source",
                    password="Backup!234567890",
                    url="https://backup.test",
                    folder="Development",
                    entry_type="Login",
                    notes="from backup",
                )
            )
            source.export_path(backup_path, "restore passphrase")

            target = VaultController(tmp_path / "target.sqlite3")
            target.create_vault("target@example.local", "another correct battery staple")
            target.add_entry(
                CredentialEntry(
                    service="Local Entry",
                    account="Workspace",
                    username="target",
                    password="Local!234567890",
                    url="https://local.test",
                    folder="Creative",
                    entry_type="Login",
                    notes="local",
                )
            )

            self.assertEqual(target.restore_path(backup_path, "restore passphrase"), 1)
            entries = target.list_entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].service, "Backup Entry")

    def test_travel_mode_keeps_safe_entries_and_restores_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            controller = VaultController(tmp_path / "rat.sqlite3")
            controller.create_vault("rat@example.local", "correct horse battery staple")
            controller.add_entry(
                CredentialEntry(
                    service="Safe",
                    account="Workspace",
                    username="safe",
                    password="Safe!234567890",
                    url="https://safe.test",
                    folder="Development",
                    entry_type="Login",
                    notes="safe",
                    favorite=True,
                )
            )
            controller.add_entry(
                CredentialEntry(
                    service="Sensitive",
                    account="Workspace",
                    username="sensitive",
                    password="Sensitive!234567890",
                    url="https://sensitive.test",
                    folder="Infrastructure",
                    entry_type="Login",
                    notes="sensitive",
                )
            )

            travel_path = tmp_path / "travel.rattravel"
            result = controller.activate_travel_mode(travel_path, "travel passphrase")
            self.assertEqual(result["removed"], 1)
            self.assertTrue(controller.is_travel_mode_active())
            self.assertEqual([entry.service for entry in controller.list_entries()], ["Safe"])

            restored = controller.deactivate_travel_mode(travel_path, "travel passphrase")
            self.assertEqual(restored, 2)
            self.assertFalse(controller.is_travel_mode_active())
            self.assertEqual({entry.service for entry in controller.list_entries()}, {"Safe", "Sensitive"})

    def test_preferences_failed_unlock_and_self_destruct(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "rat.sqlite3"
            controller = VaultController(db_path)
            controller.create_vault("rat@example.local", "correct horse battery staple")
            controller.set_setting("auto_lock_minutes", 3)
            controller.set_setting("clipboard_clear_seconds", 17)
            controller.set_setting("mask_usernames", True)
            self.assertEqual(controller.setting_int("auto_lock_minutes"), 3)
            self.assertEqual(controller.setting_int("clipboard_clear_seconds"), 17)
            self.assertTrue(controller.setting_bool("mask_usernames"))

            controller.set_setting("self_destruct_enabled", True)
            controller.set_setting("self_destruct_failed_attempts", 2)
            self.assertFalse(controller.register_failed_unlock())
            self.assertTrue(controller.register_failed_unlock())
            success, _message = controller.self_destruct()
            self.assertTrue(success)
            self.assertFalse(db_path.exists())

    def test_password_health_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "rat.sqlite3"
            controller = VaultController(db_path)
            controller.create_vault("rat@example.local", "correct horse battery staple")
            controller.add_entry(
                CredentialEntry(
                    service="Weak",
                    account="Workspace",
                    username="",
                    password="short",
                    url="",
                    folder="Development",
                    entry_type="Login",
                    notes="weak",
                )
            )
            controller.add_entry(
                CredentialEntry(
                    service="Strong",
                    account="Workspace",
                    username="strong",
                    password="Strong!234567890",
                    url="https://strong.test",
                    folder="Creative",
                    entry_type="Login",
                    notes="strong",
                )
            )
            report = controller.password_health_report()
            self.assertEqual(report["total"], 2)
            self.assertEqual(report["strong"], 1)
            self.assertEqual(report["weak"], 1)

    def test_demo_vault_uses_isolated_database(self) -> None:
        original_home = os.environ.get("RAT_VAULT_HOME")
        original_db = os.environ.get("RAT_VAULT_DB_PATH")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.environ["RAT_VAULT_HOME"] = tmp
                os.environ.pop("RAT_VAULT_DB_PATH", None)
                self.assertNotEqual(default_vault_db_path(), demo_vault_db_path())

                controller = VaultController(demo_vault_db_path())
                controller.create_vault("rat@vault.local", "ratmode-demo-2026")
                controller.lock()
                controller.unlock_vault("rat@vault.local", "ratmode-demo-2026")
                self.assertTrue(controller.unlocked)
                self.assertEqual(controller.db_path.name, "rat-mode-demo.vault.sqlite3")
            finally:
                if original_home is None:
                    os.environ.pop("RAT_VAULT_HOME", None)
                else:
                    os.environ["RAT_VAULT_HOME"] = original_home
                if original_db is None:
                    os.environ.pop("RAT_VAULT_DB_PATH", None)
                else:
                    os.environ["RAT_VAULT_DB_PATH"] = original_db


if __name__ == "__main__":
    unittest.main()
