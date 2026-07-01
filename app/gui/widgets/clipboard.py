from __future__ import annotations

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication


class SecureClipboard:
    def __init__(self, clear_after_ms: int = 30_000):
        self.clear_after_ms = clear_after_ms

    def copy(self, value: str, on_clear=None) -> None:
        QApplication.clipboard().setText(value)
        QTimer.singleShot(self.clear_after_ms, lambda copied=value: self.clear_if_unchanged(copied, on_clear))

    def clear_if_unchanged(self, copied: str, on_clear=None) -> None:
        clipboard = QApplication.clipboard()
        if clipboard.text() == copied:
            clipboard.clear()
            if on_clear:
                on_clear()

