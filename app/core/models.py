from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CredentialEntry:
    service: str
    account: str
    username: str
    password: str
    url: str
    folder: str
    entry_type: str
    notes: str
    health: str = "Strong"
    updated: str = "Today"
    favorite: bool = False
    id: int | None = None
    custom_fields: dict[str, str] = field(default_factory=dict)

    @property
    def masked_password(self) -> str:
        return "*" * max(10, min(len(self.password), 18))

    def searchable_text(self) -> str:
        values = [
            self.service,
            self.account,
            self.username,
            self.url,
            self.folder,
            self.entry_type,
            self.notes,
            self.health,
            *self.custom_fields.keys(),
            *self.custom_fields.values(),
        ]
        return " ".join(value for value in values if value).lower()

    def to_plain_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "account": self.account,
            "username": self.username,
            "password": self.password,
            "url": self.url,
            "folder": self.folder,
            "entry_type": self.entry_type,
            "notes": self.notes,
            "health": self.health,
            "favorite": self.favorite,
            "custom_fields": dict(self.custom_fields),
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "CredentialEntry":
        password = data.get("password", "")
        if isinstance(password, dict):
            password = password.get("value", "")

        favorite = data.get("favorite", False)
        if isinstance(favorite, str):
            favorite = favorite.strip().lower() in {"1", "true", "yes", "on"}

        return cls(
            service=str(data.get("service") or data.get("website") or data.get("title") or data.get("name") or "").strip(),
            account=str(data.get("account") or data.get("account_name") or data.get("workspace") or "").strip(),
            username=str(data.get("username") or data.get("user") or data.get("login") or "").strip(),
            password=str(password or ""),
            url=str(data.get("url") or data.get("uri") or data.get("website_url") or "").strip(),
            folder=str(data.get("folder") or data.get("folder_name") or "Imported").strip() or "Imported",
            entry_type=str(data.get("entry_type") or data.get("type") or data.get("category") or "Login").strip() or "Login",
            notes=str(data.get("notes") or data.get("note") or data.get("description") or "").strip(),
            health=str(data.get("health") or "Strong"),
            favorite=bool(favorite),
            custom_fields=dict(data.get("custom_fields") or {}),
        )


@dataclass(frozen=True)
class VaultSummary:
    entries: int
    folders: int
    weak_entries: int
    storage_label: str
    database_path: str
