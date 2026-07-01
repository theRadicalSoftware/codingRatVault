from __future__ import annotations

import base64
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .crypto import KDF_ITERATIONS, b64d, b64e, derive_key
from .models import CredentialEntry


RAT_EXPORT_FORMAT = "coding-rat-vault-export"
RAT_EXPORT_VERSION = 1
EXPORT_AAD = b"rat-vault:export:v1"
SUPPORTED_IMPORT_EXTENSIONS = {".json", ".csv", ".cvbak", ".ratvault", ".rattravel"}


def build_encrypted_export(entries: list[CredentialEntry], passphrase: str) -> dict[str, Any]:
    if not passphrase:
        raise ValueError("Export passphrase is required")
    salt = random_bytes(16)
    nonce = random_bytes(12)
    key = derive_key(passphrase, salt, KDF_ITERATIONS)
    aesgcm = AESGCM(key)
    payload = {
        "format": RAT_EXPORT_FORMAT,
        "version": RAT_EXPORT_VERSION,
        "exported_at": datetime.now().replace(microsecond=0).isoformat(),
        "entries": [entry.to_plain_dict() for entry in entries],
    }
    plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, EXPORT_AAD)
    return {
        "format": RAT_EXPORT_FORMAT,
        "version": RAT_EXPORT_VERSION,
        "encrypted": True,
        "cipher": "aes-256-gcm",
        "kdf": {"name": "pbkdf2-sha256", "iterations": KDF_ITERATIONS, "salt": b64e(salt)},
        "nonce": b64e(nonce),
        "payload": b64e(ciphertext),
    }


def load_entries_from_path(path: Path | str, passphrase: str | None = None) -> list[CredentialEntry]:
    target = Path(path).expanduser()
    if target.is_dir():
        entries: list[CredentialEntry] = []
        for child in sorted(target.rglob("*")):
            if child.is_file() and child.suffix.lower() in SUPPORTED_IMPORT_EXTENSIONS:
                entries.extend(load_entries_from_file(child, passphrase=passphrase))
        return entries
    return load_entries_from_file(target, passphrase=passphrase)


def load_entries_from_file(path: Path | str, passphrase: str | None = None) -> list[CredentialEntry]:
    target = Path(path).expanduser()
    suffix = target.suffix.lower()
    if suffix == ".csv":
        return _load_csv(target)
    if suffix in {".json", ".cvbak", ".ratvault", ".rattravel"}:
        data = json.loads(target.read_text(encoding="utf-8"))
        data = _decrypt_if_needed(data, passphrase)
        return _entries_from_document(data)
    raise ValueError(f"Unsupported import file type: {target.suffix}")


def write_export_file(path: Path | str, entries: list[CredentialEntry], passphrase: str) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    package = build_encrypted_export(entries, passphrase)
    target.write_text(json.dumps(package, indent=2), encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass


def _decrypt_if_needed(data: dict[str, Any], passphrase: str | None) -> dict[str, Any]:
    if data.get("format") == RAT_EXPORT_FORMAT and data.get("encrypted"):
        if not passphrase:
            raise ValueError("Rat export requires its export passphrase")
        kdf = data.get("kdf") or {}
        key = derive_key(passphrase, b64d(kdf["salt"]), int(kdf.get("iterations", KDF_ITERATIONS)))
        plaintext = AESGCM(key).decrypt(b64d(data["nonce"]), b64d(data["payload"]), EXPORT_AAD)
        return json.loads(plaintext.decode("utf-8"))

    if "salt" in data and "data" in data:
        if not passphrase:
            raise ValueError("Kitty .cvbak import requires the old backup passphrase")
        return _decrypt_kitty_v1_backup(data, passphrase)

    return data


def _decrypt_kitty_v1_backup(data: dict[str, Any], passphrase: str) -> dict[str, Any]:
    salt = base64.b64decode(data["salt"])
    encrypted_data = base64.b64decode(data["data"])
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    plaintext = Fernet(key).decrypt(encrypted_data)
    return json.loads(plaintext.decode("utf-8"))


def _entries_from_document(data: Any) -> list[CredentialEntry]:
    if isinstance(data, list):
        raw_entries = data
        folders_by_id = {}
    elif isinstance(data, dict):
        raw_entries = data.get("entries") or data.get("items") or []
        folders_by_id = {
            folder.get("id"): folder.get("name")
            for folder in data.get("folders", [])
            if isinstance(folder, dict)
        }
    else:
        raise ValueError("Import document must be a JSON object or array")

    entries: list[CredentialEntry] = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            continue
        normalized = dict(raw)
        if not normalized.get("folder") and normalized.get("folder_id") in folders_by_id:
            normalized["folder"] = folders_by_id.get(normalized.get("folder_id"))
        entry = CredentialEntry.from_mapping(normalized)
        if entry.service and entry.password:
            entries.append(entry)
    return entries


def _load_csv(path: Path) -> list[CredentialEntry]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return [
            CredentialEntry.from_mapping(row)
            for row in rows
            if row and (row.get("service") or row.get("website") or row.get("name")) and row.get("password")
        ]


def random_bytes(length: int) -> bytes:
    import os

    return os.urandom(length)
