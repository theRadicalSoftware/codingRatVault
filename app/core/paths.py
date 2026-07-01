from __future__ import annotations

import os
from pathlib import Path


APP_DIR_NAME = "coding-rat-vault"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_home() -> Path:
    override = os.environ.get("RAT_VAULT_HOME")
    if override:
        return Path(override).expanduser().resolve()

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser().resolve() / APP_DIR_NAME

    return Path.home() / ".local" / "share" / APP_DIR_NAME


def default_vault_db_path() -> Path:
    override = os.environ.get("RAT_VAULT_DB_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return data_home() / "rat-mode.vault.sqlite3"


def demo_vault_db_path() -> Path:
    return data_home() / "rat-mode-demo.vault.sqlite3"


def default_export_dir() -> Path:
    return data_home() / "exports"


def ensure_private_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
