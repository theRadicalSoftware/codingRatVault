from __future__ import annotations

import hashlib
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class BreachResult:
    checked: bool
    count: int = 0
    error: str = ""


class BreachMonitor:
    """HIBP k-anonymity password check with a tiny in-memory prefix cache."""

    def __init__(self):
        self._cache: dict[str, str] = {}

    def check_password(self, password: str, timeout: float = 5.0) -> BreachResult:
        if not password:
            return BreachResult(checked=False, error="Empty password")

        digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = digest[:5], digest[5:]
        try:
            body = self._cache.get(prefix)
            if body is None:
                request = urllib.request.Request(
                    f"https://api.pwnedpasswords.com/range/{prefix}",
                    headers={"Add-Padding": "true", "User-Agent": "CodingRatVault/0.2"},
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = response.read().decode("utf-8")
                self._cache[prefix] = body

            for line in body.splitlines():
                candidate, _, count = line.partition(":")
                if candidate == suffix:
                    return BreachResult(checked=True, count=int(count or "0"))
            return BreachResult(checked=True, count=0)
        except Exception as exc:
            return BreachResult(checked=False, error=str(exc))

