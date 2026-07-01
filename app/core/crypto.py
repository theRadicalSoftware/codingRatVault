from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


CIPHER_MAGIC = b"RMV1"
CIPHER_NONCE_BYTES = 12
KDF_NAME = "pbkdf2-sha256"
KDF_ITERATIONS = 600_000
SALT_BYTES = 16
KEY_BYTES = 32
VERIFICATION_TEXT = "coding-rat-vault:verification:v1"


@dataclass(frozen=True)
class KdfParams:
    salt: bytes
    iterations: int = KDF_ITERATIONS
    name: str = KDF_NAME


class VaultCrypto:
    """AES-GCM encryption with a versioned ciphertext envelope."""

    def __init__(self, key: bytes):
        if len(key) != KEY_BYTES:
            raise ValueError(f"Vault key must be {KEY_BYTES} bytes")
        self._key = bytes(key)
        self._aesgcm = AESGCM(self._key)

    @classmethod
    def from_password(cls, master_password: str, params: KdfParams) -> "VaultCrypto":
        if params.name != KDF_NAME:
            raise ValueError(f"Unsupported KDF: {params.name}")
        return cls(derive_key(master_password, params.salt, params.iterations))

    @classmethod
    def create(cls, master_password: str) -> tuple["VaultCrypto", KdfParams]:
        params = KdfParams(salt=os.urandom(SALT_BYTES))
        return cls.from_password(master_password, params), params

    def encrypt(self, plaintext: bytes, aad: bytes) -> bytes:
        nonce = os.urandom(CIPHER_NONCE_BYTES)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, aad)
        return CIPHER_MAGIC + nonce + ciphertext

    def decrypt(self, token: bytes, aad: bytes) -> bytes:
        if not token.startswith(CIPHER_MAGIC):
            raise ValueError("Unsupported ciphertext envelope")
        nonce_start = len(CIPHER_MAGIC)
        nonce_end = nonce_start + CIPHER_NONCE_BYTES
        nonce = token[nonce_start:nonce_end]
        ciphertext = token[nonce_end:]
        try:
            return self._aesgcm.decrypt(nonce, ciphertext, aad)
        except InvalidTag as exc:
            raise ValueError("Encrypted data failed authentication") from exc

    def encrypt_text(self, value: str, aad: bytes) -> bytes:
        return self.encrypt((value or "").encode("utf-8"), aad)

    def decrypt_text(self, token: bytes | None, aad: bytes) -> str:
        if token is None:
            return ""
        return self.decrypt(token, aad).decode("utf-8")

    def encrypt_json(self, value: dict[str, Any], aad: bytes) -> bytes:
        payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return self.encrypt(payload, aad)

    def decrypt_json(self, token: bytes, aad: bytes) -> dict[str, Any]:
        return json.loads(self.decrypt(token, aad).decode("utf-8"))


def derive_key(master_password: str, salt: bytes, iterations: int = KDF_ITERATIONS) -> bytes:
    if not master_password:
        raise ValueError("Master passphrase is required")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_BYTES,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(master_password.encode("utf-8"))


def make_verification_token(crypto: VaultCrypto) -> bytes:
    return crypto.encrypt_text(VERIFICATION_TEXT, verification_aad())


def verify_token(crypto: VaultCrypto, token: bytes) -> bool:
    try:
        return hmac.compare_digest(crypto.decrypt_text(token, verification_aad()), VERIFICATION_TEXT)
    except Exception:
        return False


def verification_aad() -> bytes:
    return b"rat-vault:verification:v1"


def access_id_hash(access_id: str, salt: bytes) -> str:
    normalized = access_id.strip().lower().encode("utf-8")
    return hashlib.sha256(b"rat-vault-access:" + salt + normalized).hexdigest()


def entry_aad(uid: str, field: str) -> bytes:
    return f"rat-vault:entry:v1:{uid}:{field}".encode("utf-8")


def custom_field_aad(entry_uid: str, field_uid: str, field: str) -> bytes:
    return f"rat-vault:custom-field:v1:{entry_uid}:{field_uid}:{field}".encode("utf-8")


def b64e(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def b64d(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def zero_bytearray(value: bytearray) -> None:
    for index in range(len(value)):
        value[index] = 0
    value.clear()

