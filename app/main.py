from __future__ import annotations

import secrets
import string
import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.models import CredentialEntry
from app.core.paths import default_export_dir, demo_vault_db_path
from app.core.security.breach import BreachMonitor
from app.gui.controllers.vault_controller import VaultController
from app.gui.widgets.clipboard import SecureClipboard


APP_NAME = "Coding Rat Vault"
APP_VERSION = "0.2.0"
DEMO_ACCESS_ID = "rat@vault.local"
DEMO_PASSPHRASE = "ratmode-demo-2026"
MAGENTA = "#ff3f91"
MAGENTA_SOFT = "#ff6aa9"
INK = "#050608"
CHARCOAL = "#101217"
GRAPHITE = "#1b1e24"
MUTED = "#9da1ad"
TEXT = "#f1f3f8"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def asset_path(name: str) -> Path:
    return project_root() / "assets" / name


class RatModeBackdrop(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.wallpaper = QPixmap(str(asset_path("coding-rat-wallpaper.png")))
        self.phase = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(42)

    def tick(self) -> None:
        self.phase = (self.phase + 1) % 10000
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(INK))

        if not self.wallpaper.isNull():
            scaled = self.wallpaper.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = self.width() - scaled.width()
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

        wash = QLinearGradient(0, 0, self.width(), 0)
        wash.setColorAt(0.0, QColor(0, 0, 0, 245))
        wash.setColorAt(0.36, QColor(3, 5, 8, 225))
        wash.setColorAt(0.62, QColor(6, 7, 10, 118))
        wash.setColorAt(1.0, QColor(0, 0, 0, 75))
        painter.fillRect(self.rect(), wash)

        top_wash = QLinearGradient(0, 0, 0, self.height())
        top_wash.setColorAt(0.0, QColor(0, 0, 0, 150))
        top_wash.setColorAt(0.50, QColor(0, 0, 0, 0))
        top_wash.setColorAt(1.0, QColor(0, 0, 0, 138))
        painter.fillRect(self.rect(), top_wash)

        self.draw_grid(painter)
        self.draw_signal_noise(painter)

    def draw_grid(self, painter: QPainter) -> None:
        painter.save()
        painter.setPen(QPen(QColor(255, 63, 145, 18), 1))
        left_limit = int(self.width() * 0.48)
        for x in range(0, left_limit, 42):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 42):
            painter.drawLine(0, y, left_limit, y)
        painter.restore()

    def draw_signal_noise(self, painter: QPainter) -> None:
        painter.save()
        for i in range(36):
            seed = (i * 97 + self.phase * 3) % 997
            x = int((seed / 997) * self.width())
            y = int(((seed * 37) % 997 / 997) * self.height())
            if x > self.width() * 0.56 and i % 3:
                continue
            alpha = 28 + (i % 5) * 12
            painter.setPen(QPen(QColor(255, 63, 145, alpha), 1))
            painter.drawLine(x, y, x + 18 + (i % 4) * 11, y)

        painter.setPen(QPen(QColor(255, 63, 145, 24), 1))
        for y in range((self.phase // 2) % 9, self.height(), 9):
            painter.drawLine(0, y, self.width(), y)
        painter.restore()


class RatSeal(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(58, 58)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        size = min(self.width(), self.height())
        pad = max(3, round(size * 0.07))
        rect = QRectF(pad, pad, size - pad * 2, size - pad * 2)

        glow = QColor(255, 63, 145, 58)
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect.adjusted(-pad, -pad, pad, pad))

        painter.setBrush(QColor(8, 9, 12, 235))
        painter.setPen(QPen(QColor(255, 63, 145, 150), 1.4))
        painter.drawEllipse(rect)

        painter.setBrush(QColor(255, 63, 145, 225))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(size * 0.24, size * 0.23, size * 0.22, size * 0.22))
        painter.drawEllipse(QRectF(size * 0.54, size * 0.23, size * 0.22, size * 0.22))
        painter.drawEllipse(QRectF(size * 0.35, size * 0.40, size * 0.30, size * 0.30))

        painter.setBrush(QColor(9, 10, 13, 240))
        painter.drawEllipse(QRectF(size * 0.38, size * 0.47, size * 0.07, size * 0.07))
        painter.drawEllipse(QRectF(size * 0.58, size * 0.47, size * 0.07, size * 0.07))

        painter.setBrush(QColor(255, 63, 145, 170))
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.59)
        path.lineTo(size * 0.58, size * 0.59)
        path.lineTo(size * 0.54, size * 0.65)
        path.closeSubpath()
        painter.drawPath(path)


class ModeButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


class NavButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(42)
        self.setObjectName("navButton")


class StatCard(QFrame):
    def __init__(self, label: str, value: str, detail: str):
        super().__init__()
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(5)

        label_widget = QLabel(label.upper())
        label_widget.setObjectName("statLabel")
        self.value_widget = QLabel(value)
        self.value_widget.setObjectName("statValue")
        self.detail_widget = QLabel(detail)
        self.detail_widget.setObjectName("statDetail")
        self.detail_widget.setWordWrap(True)

        layout.addWidget(label_widget)
        layout.addWidget(self.value_widget)
        layout.addWidget(self.detail_widget)

    def update_values(self, value: str, detail: str) -> None:
        self.value_widget.setText(value)
        self.detail_widget.setText(detail)


class SectionPanel(QFrame):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("sectionPanel")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 18)
        self.layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)

        title_widget = QLabel(title)
        title_widget.setObjectName("sectionTitle")
        title_stack.addWidget(title_widget)

        if subtitle:
            subtitle_widget = QLabel(subtitle)
            subtitle_widget.setObjectName("sectionSubtitle")
            subtitle_widget.setWordWrap(True)
            title_stack.addWidget(subtitle_widget)

        header.addLayout(title_stack)
        header.addStretch(1)
        self.layout.addLayout(header)


class FolderMapWidget(QFrame):
    folder_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("folderMap")
        self.setMinimumWidth(132)
        self.folders: list[tuple[str, int]] = []
        self.active_folder = "All"
        self.node_buttons: dict[str, QPushButton] = {}
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_folders(self, folders: list[tuple[str, int]], active_folder: str) -> None:
        self.folders = folders
        self.active_folder = active_folder if active_folder else "All"
        self.rebuild_nodes()

    def rebuild_nodes(self) -> None:
        for button in self.node_buttons.values():
            button.deleteLater()
        self.node_buttons.clear()

        for folder, count in self.folders:
            button = QPushButton(f"{folder}\n{count} item{'s' if count != 1 else ''}", self)
            button.setObjectName("folderNodeButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(f"Show {folder.lower()} credentials" if folder != "All" else "Show all credentials")
            button.clicked.connect(lambda _checked=False, name=folder: self.choose_folder(name))
            self.node_buttons[folder] = button

        self.position_nodes()
        self.update_active_styles()
        self.update()

    def choose_folder(self, folder: str) -> None:
        self.active_folder = folder
        self.update_active_styles()
        self.folder_selected.emit(folder)
        self.update()

    def update_active_styles(self) -> None:
        for folder, button in self.node_buttons.items():
            button.setChecked(folder == self.active_folder)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.position_nodes()

    def position_nodes(self) -> None:
        if not self.node_buttons:
            return

        wide_layout = self.width() >= 260
        max_node_w = 168 if wide_layout else 142
        available_w = (self.width() - 72) // 2 if wide_layout else self.width() - 24
        node_w = max(118, min(max_node_w, available_w))
        node_h = 44
        center_x = max(14, (self.width() - node_w) // 2)
        root = self.node_buttons.get("All")
        if root:
            root.move(center_x, 12)
            root.resize(node_w, node_h)

        children = [name for name, _count in self.folders if name != "All"]
        if wide_layout:
            left_x = max(18, (self.width() - (node_w * 2 + 34)) // 2)
            right_x = left_x + node_w + 34
            for index, name in enumerate(children):
                button = self.node_buttons.get(name)
                if not button:
                    continue
                row = index // 2
                x = center_x if index == len(children) - 1 and len(children) % 2 else (left_x if index % 2 == 0 else right_x)
                button.move(x, 92 + row * 78)
                button.resize(node_w, node_h)
        else:
            y = 82
            for name in children:
                button = self.node_buttons.get(name)
                if button:
                    button.move(center_x, y)
                    button.resize(node_w, node_h)
                y += 54

    def node_center(self, name: str) -> QPointF | None:
        button = self.node_buttons.get(name)
        if not button:
            return None
        geo = button.geometry()
        return QPointF(geo.center())

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if "All" not in self.node_buttons:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor(255, 63, 145, 72), 1.2))

        root = self.node_center("All")
        if root is None:
            return

        children = [(folder, self.node_center(folder)) for folder, _count in self.folders if folder != "All"]
        children = [(folder, center) for folder, center in children if center is not None]
        if not children:
            return

        trunk_x = max(16, root.x() - 26)
        painter.drawLine(int(root.x()), int(root.y() + 22), int(trunk_x), int(root.y() + 22))
        painter.drawLine(int(trunk_x), int(root.y() + 22), int(trunk_x), int(children[-1][1].y()))

        for folder, child in children:
            if folder == "All":
                continue
            if child is None:
                continue
            path = QPainterPath()
            path.moveTo(trunk_x, child.y())
            path.lineTo(child.x() - 20, child.y())
            path.quadTo(child.x() - 10, child.y(), child.x(), child.y())
            painter.drawPath(path)


class BreachCheckWorker(QThread):
    progress_update = pyqtSignal(int, int)
    check_complete = pyqtSignal(str)

    def __init__(self, entries: list[CredentialEntry]):
        super().__init__()
        self.entries = entries

    def run(self) -> None:
        if not self.entries:
            self.check_complete.emit("No credentials to check")
            return

        monitor = BreachMonitor()
        checked = 0
        compromised: list[str] = []
        errors = 0
        total = len(self.entries)

        for index, entry in enumerate(self.entries, start=1):
            result = monitor.check_password(entry.password)
            if result.checked:
                checked += 1
                if result.count:
                    compromised.append(entry.service)
            else:
                errors += 1
            self.progress_update.emit(index, total)

        if compromised:
            names = ", ".join(compromised[:4])
            extra = f" and {len(compromised) - 4} more" if len(compromised) > 4 else ""
            self.check_complete.emit(f"{len(compromised)} exposed password{'s' if len(compromised) != 1 else ''}: {names}{extra}")
        elif checked:
            suffix = f"; {errors} unavailable" if errors else ""
            self.check_complete.emit(f"{checked} passwords clear{suffix}")
        else:
            self.check_complete.emit("Breach service unavailable")


class DashboardWidget(QWidget):
    def __init__(self, on_lock, controller: VaultController):
        super().__init__()
        self.on_lock = on_lock
        self.controller = controller
        self.auto_lock_minutes = self.controller.setting_int("auto_lock_minutes", 10)
        self.clipboard_clear_seconds = self.controller.setting_int("clipboard_clear_seconds", 30)
        self.mask_usernames = self.controller.setting_bool("mask_usernames", False)
        self.clipboard = SecureClipboard(self.clipboard_clear_seconds * 1000)
        self.credentials = self.load_credentials()
        self.nav_buttons: dict[str, NavButton] = {}
        self.folder_chip_buttons: dict[str, QPushButton] = {}
        self.active_folder = "All"
        self.selected_credential: CredentialEntry | None = None
        self.visible_credentials: list[CredentialEntry] = []
        self.editing_entry_id: int | None = None
        self.breach_worker: BreachCheckWorker | None = None
        self.build_ui()
        self.refresh_all()
        self.auto_lock_timer = QTimer(self)
        self.auto_lock_timer.timeout.connect(self.handle_auto_lock)
        self.restart_auto_lock_timer()

    def load_credentials(self) -> list[CredentialEntry]:
        if self.controller.unlocked:
            return self.controller.list_entries()
        return []

    def set_controller(self, controller: VaultController) -> None:
        self.controller = controller
        self.auto_lock_minutes = self.controller.setting_int("auto_lock_minutes", 10)
        self.clipboard_clear_seconds = self.controller.setting_int("clipboard_clear_seconds", 30)
        self.mask_usernames = self.controller.setting_bool("mask_usernames", False)
        self.clipboard.clear_after_ms = self.clipboard_clear_seconds * 1000
        self.active_folder = "All"
        self.selected_credential = None
        self.credentials = self.load_credentials()
        self.refresh_all()

    def build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 28)
        root.setSpacing(18)

        root.addWidget(self.build_sidebar())

        self.content_host = QWidget()
        self.content_stack = QStackedLayout(self.content_host)
        self.content_stack.setContentsMargins(0, 0, 0, 0)
        self.overview_view = self.build_overview_view()
        self.vault_view = self.build_vault_view()
        self.detail_view = self.build_detail_view()
        self.add_entry_view = self.build_add_entry_view()
        self.generator_view = self.build_generator_view()
        self.security_view = self.build_security_view()
        self.settings_view = self.build_settings_view()
        self.content_stack.addWidget(self.overview_view)
        self.content_stack.addWidget(self.vault_view)
        self.content_stack.addWidget(self.detail_view)
        self.content_stack.addWidget(self.add_entry_view)
        self.content_stack.addWidget(self.generator_view)
        self.content_stack.addWidget(self.security_view)
        self.content_stack.addWidget(self.settings_view)
        root.addWidget(self.content_host, 1)

    def build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(226)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        seal = RatSeal()
        seal.setFixedSize(44, 44)
        brand_row.addWidget(seal)
        brand_stack = QVBoxLayout()
        brand_stack.setSpacing(0)
        brand_title = QLabel("Rat Vault")
        brand_title.setObjectName("sidebarTitle")
        brand_mode = QLabel("Session unlocked")
        brand_mode.setObjectName("sidebarSubtle")
        brand_stack.addWidget(brand_title)
        brand_stack.addWidget(brand_mode)
        brand_row.addLayout(brand_stack)
        layout.addLayout(brand_row)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        for index, label in enumerate(["Overview", "Vault", "Details", "Generator", "Security", "Settings"]):
            button = NavButton(label)
            button.clicked.connect(lambda _checked=False, name=label: self.handle_nav(name))
            self.nav_buttons[label] = button
            layout.addWidget(button)
            if index == 0:
                button.setChecked(True)

        layout.addStretch(1)

        session_box = QFrame()
        session_box.setObjectName("sessionBox")
        session_layout = QVBoxLayout(session_box)
        session_layout.setContentsMargins(12, 12, 12, 12)
        session_layout.setSpacing(6)
        session_label = QLabel("LOCAL SESSION")
        session_label.setObjectName("metricLabel")
        session_state = QLabel("Encrypted locally")
        session_state.setObjectName("sessionState")
        session_note = QLabel("Vault data stays on this machine.")
        session_note.setObjectName("sessionNote")
        session_note.setWordWrap(True)
        session_layout.addWidget(session_label)
        session_layout.addWidget(session_state)
        session_layout.addWidget(session_note)
        layout.addWidget(session_box)

        lock_button = QPushButton("Lock Vault")
        lock_button.setObjectName("secondaryButton")
        lock_button.setCursor(Qt.PointingHandCursor)
        lock_button.clicked.connect(self.on_lock)
        layout.addWidget(lock_button)

        return sidebar

    def build_overview_view(self) -> QWidget:
        view = QWidget()
        main = QVBoxLayout(view)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        eyebrow = QLabel("CODING RAT VAULT")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Command Center")
        title.setObjectName("dashboardTitle")
        subtitle = QLabel("A clean local-first workspace for credentials, checks, and focused vault maintenance.")
        subtitle.setObjectName("dashboardSubtitle")
        subtitle.setWordWrap(True)
        title_stack.addWidget(eyebrow)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack, 1)

        self.global_search_input = QLineEdit()
        self.global_search_input.setObjectName("dashboardSearch")
        self.global_search_input.setPlaceholderText("Search vault")
        self.global_search_input.setFixedWidth(260)
        self.global_search_input.returnPressed.connect(self.search_from_overview)
        header.addWidget(self.global_search_input)

        add_button = QPushButton("Add Entry")
        add_button.setObjectName("primarySmallButton")
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.clicked.connect(self.show_add_entry)
        header.addWidget(add_button)
        main.addLayout(header)

        stats = QGridLayout()
        stats.setHorizontalSpacing(12)
        stats.setVerticalSpacing(12)
        self.entries_stat = StatCard("Entries", "0", "Ready for the first credential")
        self.folders_stat = StatCard("Folders", "0", "Folders will map to vault lanes")
        self.security_stat = StatCard("Security", "Ready", "Baseline checks are staged")
        self.storage_stat = StatCard("Storage", "SQLite", "Encrypted at rest")
        cards = [self.entries_stat, self.folders_stat, self.security_stat, self.storage_stat]
        for index, card in enumerate(cards):
            stats.addWidget(card, 0, index)
        main.addLayout(stats)

        lower = QHBoxLayout()
        lower.setSpacing(16)
        lower.addWidget(self.build_vault_panel(), 3)

        right_column = QVBoxLayout()
        right_column.setSpacing(16)
        right_column.addWidget(self.build_actions_panel())
        right_column.addWidget(self.build_security_panel())
        right_column.addStretch(1)
        lower.addLayout(right_column, 2)
        main.addLayout(lower, 1)

        self.session_status = QLabel("Vault workspace initialized.")
        self.session_status.setObjectName("dashboardStatus")
        main.addWidget(self.session_status)

        return view

    def build_vault_panel(self) -> QWidget:
        panel = SectionPanel("Vault", "Recent credentials from this unlocked session.")

        tools = QHBoxLayout()
        tools.setSpacing(8)
        for label in ["All", "Favorites", "Logins", "Servers"]:
            button = QPushButton(label)
            button.setObjectName("chipButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            if label == "All":
                button.setChecked(True)
            tools.addWidget(button)
        tools.addStretch(1)
        panel.layout.addLayout(tools)

        self.overview_table = self.create_credentials_table()
        self.overview_table.setMinimumHeight(278)
        panel.layout.addWidget(self.overview_table, 1)
        return panel

    def build_actions_panel(self) -> QWidget:
        panel = SectionPanel("Quick Actions")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        actions = [
            ("New Login", "Open editor"),
            ("Generate", "Create password"),
            ("Import File", "Bring records in"),
            ("Import Folder", "Scan directory"),
            ("Export", "Encrypted backup"),
            ("Audit", "Run checks"),
        ]
        for index, (label, detail) in enumerate(actions):
            button = QPushButton(f"{label}\n{detail}")
            button.setObjectName("actionButton")
            button.setCursor(Qt.PointingHandCursor)
            if label == "New Login":
                button.clicked.connect(self.show_add_entry)
            elif label == "Generate":
                button.clicked.connect(self.show_generator)
            elif label == "Import File":
                button.clicked.connect(self.import_entries_from_file)
            elif label == "Import Folder":
                button.clicked.connect(self.import_entries_from_folder)
            elif label == "Export":
                button.clicked.connect(self.export_entries)
            elif label == "Audit":
                button.clicked.connect(self.run_breach_check)
            else:
                button.clicked.connect(lambda _checked=False, text=label: self.set_session_message(f"{text} flow comes next."))
            grid.addWidget(button, index // 2, index % 2)
        panel.layout.addLayout(grid)
        return panel

    def build_security_panel(self) -> QWidget:
        panel = SectionPanel("Security Posture")
        rows = [
            ("Master key", "Verified locally"),
            ("Clipboard", "30s auto-clear"),
            ("Breach checks", "Ready"),
            ("Backups", "Encrypted export"),
        ]
        for label, value in rows:
            row = QHBoxLayout()
            row.setSpacing(8)
            label_widget = QLabel(label)
            label_widget.setObjectName("securityLabel")
            value_widget = QLabel(value)
            value_widget.setObjectName("securityValue")
            value_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(label_widget)
            row.addStretch(1)
            row.addWidget(value_widget)
            panel.layout.addLayout(row)
        return panel

    def build_activity_panel(self) -> QWidget:
        panel = SectionPanel("Session Notes")
        notes = [
            "Portal unlock accepted.",
            "Dashboard shell attached.",
            "Encrypted store is the next build target.",
        ]
        for note in notes:
            label = QLabel(note)
            label.setObjectName("activityLine")
            label.setWordWrap(True)
            panel.layout.addWidget(label)
        return panel

    def build_vault_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        eyebrow = QLabel("CREDENTIALS")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Vault")
        title.setObjectName("dashboardTitle")
        subtitle = QLabel("Browse, filter, and route credentials from the current unlocked session.")
        subtitle.setObjectName("dashboardSubtitle")
        subtitle.setWordWrap(True)
        title_stack.addWidget(eyebrow)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack, 1)

        self.vault_search_input = QLineEdit()
        self.vault_search_input.setObjectName("dashboardSearch")
        self.vault_search_input.setPlaceholderText("Search credentials")
        self.vault_search_input.setFixedWidth(300)
        self.vault_search_input.textChanged.connect(self.refresh_vault_tables)
        header.addWidget(self.vault_search_input)

        add_button = QPushButton("Add Credential")
        add_button.setObjectName("primarySmallButton")
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.clicked.connect(self.show_add_entry)
        header.addWidget(add_button)
        layout.addLayout(header)

        self.folder_filter_row = QHBoxLayout()
        self.folder_filter_row.setSpacing(8)
        self.rebuild_folder_filter_controls()
        layout.addLayout(self.folder_filter_row)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.vault_table = self.create_credentials_table()
        self.vault_table.setMinimumHeight(430)
        self.vault_table.itemSelectionChanged.connect(self.on_vault_selection_changed)
        self.vault_table.cellDoubleClicked.connect(lambda _row, _column: self.show_detail())
        body.addWidget(self.vault_table, 5)

        map_panel = SectionPanel("Folders", "Jump by workspace lane.")
        map_panel.setMinimumWidth(420)
        self.folder_map = FolderMapWidget()
        self.folder_map.folder_selected.connect(self.set_folder_filter)
        map_panel.layout.addWidget(self.folder_map, 1)
        body.addWidget(map_panel, 5)

        layout.addLayout(body, 1)
        return view

    def build_detail_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        eyebrow = QLabel("SELECTED RECORD")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Credential Detail")
        title.setObjectName("dashboardTitle")
        subtitle = QLabel("Inspect the selected account surface from the current vault session.")
        subtitle.setObjectName("dashboardSubtitle")
        subtitle.setWordWrap(True)
        title_stack.addWidget(eyebrow)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack, 1)

        back_button = QPushButton("Back to Vault")
        back_button.setObjectName("secondaryButton")
        back_button.setCursor(Qt.PointingHandCursor)
        back_button.clicked.connect(self.show_vault)
        header.addWidget(back_button)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)

        details = SectionPanel("Credential Detail", "Selected account surface.")
        self.detail_service = QLabel("No credential selected")
        self.detail_service.setObjectName("detailTitle")
        self.detail_service.setWordWrap(True)
        self.detail_account = QLabel("Awaiting selected vault record.")
        self.detail_account.setObjectName("detailSubtle")
        self.detail_url = QLabel("")
        self.detail_url.setObjectName("detailLine")
        self.detail_username = QLabel("")
        self.detail_username.setObjectName("detailLine")
        self.detail_password = QLabel("")
        self.detail_password.setObjectName("detailLine")
        self.detail_custom_fields = QLabel("")
        self.detail_custom_fields.setObjectName("detailLine")
        self.detail_notes = QLabel("")
        self.detail_notes.setObjectName("detailNote")
        for detail_label in [
            self.detail_account,
            self.detail_url,
            self.detail_username,
            self.detail_password,
            self.detail_custom_fields,
            self.detail_notes,
        ]:
            detail_label.setWordWrap(True)

        details.layout.addWidget(self.detail_service)
        details.layout.addWidget(self.detail_account)
        details.layout.addWidget(self.detail_url)
        details.layout.addWidget(self.detail_username)
        details.layout.addWidget(self.detail_password)
        details.layout.addWidget(self.detail_custom_fields)
        details.layout.addWidget(self.detail_notes)
        details.layout.addStretch(1)
        body.addWidget(details, 3)

        actions = SectionPanel("Record Actions", "Session controls.")
        self.detail_context = QLabel("No active record")
        self.detail_context.setObjectName("detailNote")
        self.detail_context.setWordWrap(True)
        actions.layout.addWidget(self.detail_context)

        copy_user = QPushButton("Copy User")
        copy_user.setObjectName("secondaryButton")
        copy_user.setCursor(Qt.PointingHandCursor)
        copy_user.clicked.connect(lambda: self.copy_selected_value("username"))
        copy_pass = QPushButton("Copy Pass")
        copy_pass.setObjectName("secondaryButton")
        copy_pass.setCursor(Qt.PointingHandCursor)
        copy_pass.clicked.connect(lambda: self.copy_selected_value("password"))
        copy_row = QHBoxLayout()
        copy_row.addWidget(copy_user)
        copy_row.addWidget(copy_pass)
        actions.layout.addLayout(copy_row)

        edit_row = QHBoxLayout()
        edit_button = QPushButton("Edit")
        edit_button.setObjectName("secondaryButton")
        edit_button.setCursor(Qt.PointingHandCursor)
        edit_button.clicked.connect(self.edit_selected_entry)
        delete_button = QPushButton("Delete")
        delete_button.setObjectName("dangerButton")
        delete_button.setCursor(Qt.PointingHandCursor)
        delete_button.clicked.connect(self.delete_selected_entry)
        edit_row.addWidget(edit_button)
        edit_row.addWidget(delete_button)
        actions.layout.addLayout(edit_row)

        add_button = QPushButton("Add Credential")
        add_button.setObjectName("primarySmallButton")
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.clicked.connect(self.show_add_entry)
        actions.layout.addWidget(add_button)

        vault_button = QPushButton("Open Vault")
        vault_button.setObjectName("secondaryButton")
        vault_button.setCursor(Qt.PointingHandCursor)
        vault_button.clicked.connect(self.show_vault)
        actions.layout.addWidget(vault_button)
        actions.layout.addStretch(1)
        body.addWidget(actions, 2)

        layout.addLayout(body, 1)
        return view

    def build_add_entry_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        self.entry_editor_eyebrow = QLabel("NEW CREDENTIAL")
        self.entry_editor_eyebrow.setObjectName("eyebrow")
        self.entry_editor_title = QLabel("Add Entry")
        self.entry_editor_title.setObjectName("dashboardTitle")
        self.entry_editor_subtitle = QLabel("Capture account details into the encrypted local vault.")
        self.entry_editor_subtitle.setObjectName("dashboardSubtitle")
        self.entry_editor_subtitle.setWordWrap(True)
        title_stack.addWidget(self.entry_editor_eyebrow)
        title_stack.addWidget(self.entry_editor_title)
        title_stack.addWidget(self.entry_editor_subtitle)
        header.addLayout(title_stack, 1)

        self.entry_editor_cancel_button = QPushButton("Back to Vault")
        self.entry_editor_cancel_button.setObjectName("secondaryButton")
        self.entry_editor_cancel_button.setCursor(Qt.PointingHandCursor)
        self.entry_editor_cancel_button.clicked.connect(self.cancel_entry_edit)
        header.addWidget(self.entry_editor_cancel_button)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        form_panel = SectionPanel("Credential Form", "Required fields are service, account, and password.")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.service_field = QLineEdit()
        self.service_field.setObjectName("formField")
        self.service_field.setPlaceholderText("GitHub, Stripe, VPN, Database")
        self.account_field = QLineEdit()
        self.account_field.setObjectName("formField")
        self.account_field.setPlaceholderText("Workspace or account label")
        self.username_field = QLineEdit()
        self.username_field.setObjectName("formField")
        self.username_field.setPlaceholderText("Username or email")
        self.entry_password_field = QLineEdit()
        self.entry_password_field.setObjectName("formField")
        self.entry_password_field.setEchoMode(QLineEdit.Password)
        self.entry_password_field.setPlaceholderText("Password, token, or secret")
        self.url_field = QLineEdit()
        self.url_field.setObjectName("formField")
        self.url_field.setPlaceholderText("https://")
        self.folder_combo = QComboBox()
        self.folder_combo.setObjectName("comboField")
        self.folder_combo.addItems(self.available_folders())
        self.type_combo = QComboBox()
        self.type_combo.setObjectName("comboField")
        self.type_combo.addItems(self.available_entry_types())
        self.travel_safe_checkbox = QCheckBox("Travel safe")
        self.travel_safe_checkbox.setObjectName("checkField")
        self.travel_safe_checkbox.setToolTip("Keep this record available when Travel Mode removes sensitive entries.")
        self.notes_field = QTextEdit()
        self.notes_field.setObjectName("notesField")
        self.notes_field.setPlaceholderText("Short context, recovery notes, or rotation details")
        self.notes_field.setFixedHeight(66)

        form.addRow("Service", self.service_field)
        form.addRow("Account", self.account_field)
        form.addRow("Username", self.username_field)
        form.addRow("Password", self.entry_password_field)
        form.addRow("URL", self.url_field)
        form.addRow("Folder", self.folder_combo)
        form.addRow("Type", self.type_combo)
        form.addRow("Travel", self.travel_safe_checkbox)
        form.addRow("Notes", self.notes_field)
        form_panel.layout.addLayout(form)

        custom_header = QHBoxLayout()
        custom_label = QLabel("Custom Fields")
        custom_label.setObjectName("sectionSubtitle")
        custom_header.addWidget(custom_label)
        custom_header.addStretch(1)
        add_custom_button = QPushButton("Add Field")
        add_custom_button.setObjectName("secondaryButton")
        add_custom_button.setCursor(Qt.PointingHandCursor)
        add_custom_button.clicked.connect(self.add_custom_field_row)
        remove_custom_button = QPushButton("Remove Field")
        remove_custom_button.setObjectName("secondaryButton")
        remove_custom_button.setCursor(Qt.PointingHandCursor)
        remove_custom_button.clicked.connect(self.remove_selected_custom_field)
        custom_header.addWidget(add_custom_button)
        custom_header.addWidget(remove_custom_button)
        form_panel.layout.addLayout(custom_header)

        self.custom_fields_table = QTableWidget(0, 2)
        self.custom_fields_table.setObjectName("vaultTable")
        self.custom_fields_table.setHorizontalHeaderLabels(["Name", "Value"])
        self.custom_fields_table.verticalHeader().setVisible(False)
        self.custom_fields_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.custom_fields_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.custom_fields_table.setMinimumHeight(120)
        self.custom_fields_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.custom_fields_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.custom_fields_table.setAlternatingRowColors(True)
        form_panel.layout.addWidget(self.custom_fields_table)

        action_row = QHBoxLayout()
        generate_button = QPushButton("Generate")
        generate_button.setObjectName("secondaryButton")
        generate_button.setCursor(Qt.PointingHandCursor)
        generate_button.clicked.connect(self.generate_entry_password)
        self.save_entry_button = QPushButton("Save Entry")
        self.save_entry_button.setObjectName("primarySmallButton")
        self.save_entry_button.setCursor(Qt.PointingHandCursor)
        self.save_entry_button.clicked.connect(self.save_entry)
        action_row.addWidget(generate_button)
        action_row.addStretch(1)
        action_row.addWidget(self.save_entry_button)
        form_panel.layout.addLayout(action_row)
        body.addWidget(form_panel, 3)

        guidance = SectionPanel("Entry Guidance")
        for text in [
            "Use names that are easy to scan later.",
            "Keep recovery hints in notes, not full recovery codes.",
            "Folders and types are real encrypted-vault filters.",
            "Notes and custom fields are encrypted before they touch the database.",
        ]:
            label = QLabel(text)
            label.setObjectName("activityLine")
            label.setWordWrap(True)
            guidance.layout.addWidget(label)
        guidance.layout.addStretch(1)
        body.addWidget(guidance, 2)
        layout.addLayout(body, 1)
        return view

    def build_generator_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        eyebrow = QLabel("PASSWORD GENERATOR")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Generator")
        title.setObjectName("dashboardTitle")
        subtitle = QLabel("Create strong passwords for new or rotated vault records.")
        subtitle.setObjectName("dashboardSubtitle")
        subtitle.setWordWrap(True)
        title_stack.addWidget(eyebrow)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack, 1)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        generator_panel = SectionPanel("Generated Secret", "Built with Python's secrets module.")
        self.generated_password_field = QLineEdit()
        self.generated_password_field.setObjectName("formField")
        self.generated_password_field.setReadOnly(True)
        self.generated_password_field.setPlaceholderText("Generate a password")
        generator_panel.layout.addWidget(self.generated_password_field)

        controls = QHBoxLayout()
        generate_button = QPushButton("Generate")
        generate_button.setObjectName("primarySmallButton")
        generate_button.setCursor(Qt.PointingHandCursor)
        generate_button.clicked.connect(self.generate_standalone_password)
        copy_button = QPushButton("Copy")
        copy_button.setObjectName("secondaryButton")
        copy_button.setCursor(Qt.PointingHandCursor)
        copy_button.clicked.connect(self.copy_generated_password)
        use_button = QPushButton("Use In Entry")
        use_button.setObjectName("secondaryButton")
        use_button.setCursor(Qt.PointingHandCursor)
        use_button.clicked.connect(self.use_generated_password)
        controls.addWidget(generate_button)
        controls.addWidget(copy_button)
        controls.addWidget(use_button)
        controls.addStretch(1)
        generator_panel.layout.addLayout(controls)
        body.addWidget(generator_panel, 3)

        policy_panel = SectionPanel("Generator Policy")
        for text in [
            "Length: 24 characters",
            "Alphabet: letters, numbers, and symbols",
            "Clipboard: clears after 30 seconds when unchanged",
            "Storage: encrypted only after saving to the vault",
        ]:
            label = QLabel(text)
            label.setObjectName("activityLine")
            label.setWordWrap(True)
            policy_panel.layout.addWidget(label)
        policy_panel.layout.addStretch(1)
        body.addWidget(policy_panel, 2)
        layout.addLayout(body, 1)
        return view

    def build_security_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        eyebrow = QLabel("SECURITY")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Posture")
        title.setObjectName("dashboardTitle")
        subtitle = QLabel("Encryption, clipboard, activity, and breach checks for the unlocked local vault.")
        subtitle.setObjectName("dashboardSubtitle")
        subtitle.setWordWrap(True)
        title_stack.addWidget(eyebrow)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack, 1)
        breach_button = QPushButton("Run Breach Check")
        breach_button.setObjectName("primarySmallButton")
        breach_button.setCursor(Qt.PointingHandCursor)
        breach_button.clicked.connect(self.run_breach_check)
        header.addWidget(breach_button)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        posture = SectionPanel("Controls")
        self.security_rows: dict[str, QLabel] = {}
        for label, value in [
            ("Cipher", "AES-256-GCM"),
            ("Key derivation", "PBKDF2-SHA256 / 600k"),
            ("Encrypted fields", "service, account, user, password, URL, notes, custom fields"),
            ("Clipboard", "Auto-clear after 30 seconds"),
            ("Auto-lock", "10 minutes"),
            ("Travel mode", "Inactive"),
            ("Breach checks", "Ready"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(8)
            label_widget = QLabel(label)
            label_widget.setObjectName("securityLabel")
            value_widget = QLabel(value)
            value_widget.setObjectName("securityValue")
            value_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_widget.setWordWrap(True)
            self.security_rows[label] = value_widget
            row.addWidget(label_widget)
            row.addStretch(1)
            row.addWidget(value_widget)
            posture.layout.addLayout(row)
        posture.layout.addStretch(1)
        body.addWidget(posture, 3)

        activity = SectionPanel("Recent Activity")
        self.activity_labels: list[QLabel] = []
        for _index in range(8):
            label = QLabel("")
            label.setObjectName("activityLine")
            label.setWordWrap(True)
            self.activity_labels.append(label)
            activity.layout.addWidget(label)
        activity.layout.addStretch(1)
        body.addWidget(activity, 3)
        layout.addLayout(body, 1)

        health = SectionPanel("Password Health", "Local review of weak, reused, and incomplete records.")
        health_stats = QHBoxLayout()
        health_stats.setSpacing(10)
        self.health_total_label = QLabel("0 entries")
        self.health_total_label.setObjectName("activityLine")
        self.health_strong_label = QLabel("0 strong")
        self.health_strong_label.setObjectName("activityLine")
        self.health_review_label = QLabel("0 review")
        self.health_review_label.setObjectName("activityLine")
        self.health_weak_label = QLabel("0 weak")
        self.health_weak_label.setObjectName("activityLine")
        for label in [self.health_total_label, self.health_strong_label, self.health_review_label, self.health_weak_label]:
            label.setWordWrap(True)
            health_stats.addWidget(label)
        health.layout.addLayout(health_stats)

        self.health_table = QTableWidget(0, 4)
        self.health_table.setObjectName("vaultTable")
        self.health_table.setHorizontalHeaderLabels(["Service", "Folder", "Status", "Issues"])
        self.health_table.verticalHeader().setVisible(False)
        self.health_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.health_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.health_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.health_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.health_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.health_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.health_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.health_table.setMinimumHeight(210)
        health.layout.addWidget(self.health_table)
        layout.addWidget(health)
        return view

    def build_settings_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        eyebrow = QLabel("VAULT SETTINGS")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Settings")
        title.setObjectName("dashboardTitle")
        subtitle = QLabel("Local storage, imports, exports, and backup maintenance.")
        subtitle.setObjectName("dashboardSubtitle")
        subtitle.setWordWrap(True)
        title_stack.addWidget(eyebrow)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack, 1)
        layout.addLayout(header)

        body = QGridLayout()
        body.setHorizontalSpacing(16)
        body.setVerticalSpacing(16)
        storage = SectionPanel("Storage")
        self.database_path_label = QLabel(str(self.controller.db_path))
        self.database_path_label.setObjectName("detailNote")
        self.database_path_label.setWordWrap(True)
        storage.layout.addWidget(self.database_path_label)
        for text in [
            "Runtime vault data is stored outside the public repository.",
            "Repository .gitignore still blocks accidental local vault files, backups, and exports.",
            "Exports are encrypted with a separate export passphrase.",
        ]:
            label = QLabel(text)
            label.setObjectName("activityLine")
            label.setWordWrap(True)
            storage.layout.addWidget(label)
        storage.layout.addStretch(1)
        body.addWidget(storage, 0, 0)

        transfer = SectionPanel("Import / Export")
        import_file = QPushButton("Import File")
        import_file.setObjectName("secondaryButton")
        import_file.setCursor(Qt.PointingHandCursor)
        import_file.clicked.connect(self.import_entries_from_file)
        import_folder = QPushButton("Import Folder")
        import_folder.setObjectName("secondaryButton")
        import_folder.setCursor(Qt.PointingHandCursor)
        import_folder.clicked.connect(self.import_entries_from_folder)
        export_button = QPushButton("Export Backup")
        export_button.setObjectName("primarySmallButton")
        export_button.setCursor(Qt.PointingHandCursor)
        export_button.clicked.connect(self.export_entries)
        restore_button = QPushButton("Restore Backup")
        restore_button.setObjectName("secondaryButton")
        restore_button.setCursor(Qt.PointingHandCursor)
        restore_button.clicked.connect(self.restore_entries)
        transfer.layout.addWidget(import_file)
        transfer.layout.addWidget(import_folder)
        transfer.layout.addWidget(export_button)
        transfer.layout.addWidget(restore_button)
        self.transfer_status = QLabel("Supports Rat encrypted exports, CSV, JSON, and Kitty V1 .cvbak with passphrase.")
        self.transfer_status.setObjectName("detailNote")
        self.transfer_status.setWordWrap(True)
        transfer.layout.addWidget(self.transfer_status)
        transfer.layout.addStretch(1)
        body.addWidget(transfer, 0, 1)

        folders = SectionPanel("Folders")
        self.folder_manager_table = QTableWidget(0, 1)
        self.folder_manager_table.setObjectName("vaultTable")
        self.folder_manager_table.setHorizontalHeaderLabels(["Folder"])
        self.folder_manager_table.verticalHeader().setVisible(False)
        self.folder_manager_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.folder_manager_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.folder_manager_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.folder_manager_table.setMinimumHeight(180)
        folders.layout.addWidget(self.folder_manager_table)

        folder_actions = QHBoxLayout()
        add_folder = QPushButton("Add")
        add_folder.setObjectName("secondaryButton")
        add_folder.setCursor(Qt.PointingHandCursor)
        add_folder.clicked.connect(self.add_folder)
        rename_folder = QPushButton("Rename")
        rename_folder.setObjectName("secondaryButton")
        rename_folder.setCursor(Qt.PointingHandCursor)
        rename_folder.clicked.connect(self.rename_selected_folder)
        delete_folder = QPushButton("Delete")
        delete_folder.setObjectName("dangerButton")
        delete_folder.setCursor(Qt.PointingHandCursor)
        delete_folder.clicked.connect(self.delete_selected_folder)
        folder_actions.addWidget(add_folder)
        folder_actions.addWidget(rename_folder)
        folder_actions.addWidget(delete_folder)
        folders.layout.addLayout(folder_actions)
        self.folder_manager_status = QLabel("Deleting a folder moves its records to Imported.")
        self.folder_manager_status.setObjectName("detailNote")
        self.folder_manager_status.setWordWrap(True)
        folders.layout.addWidget(self.folder_manager_status)
        folders.layout.addStretch(1)
        body.addWidget(folders, 0, 2)

        travel = SectionPanel("Travel Mode", "Keep only records marked travel safe after creating an encrypted backup.")
        self.travel_mode_status = QLabel("Inactive")
        self.travel_mode_status.setObjectName("detailNote")
        self.travel_mode_status.setWordWrap(True)
        travel.layout.addWidget(self.travel_mode_status)
        travel_actions = QHBoxLayout()
        activate_travel = QPushButton("Activate")
        activate_travel.setObjectName("primarySmallButton")
        activate_travel.setCursor(Qt.PointingHandCursor)
        activate_travel.clicked.connect(self.activate_travel_mode)
        restore_travel = QPushButton("Restore")
        restore_travel.setObjectName("secondaryButton")
        restore_travel.setCursor(Qt.PointingHandCursor)
        restore_travel.clicked.connect(self.restore_travel_mode)
        travel_actions.addWidget(activate_travel)
        travel_actions.addWidget(restore_travel)
        travel.layout.addLayout(travel_actions)
        self.travel_mode_note = QLabel("Mark entries as Travel safe in the credential editor before activating.")
        self.travel_mode_note.setObjectName("activityLine")
        self.travel_mode_note.setWordWrap(True)
        travel.layout.addWidget(self.travel_mode_note)
        travel.layout.addStretch(1)
        body.addWidget(travel, 1, 0)

        preferences = SectionPanel("Preferences", "Runtime behavior for the unlocked vault.")
        pref_form = QFormLayout()
        self.auto_lock_spin = QSpinBox()
        self.auto_lock_spin.setObjectName("comboField")
        self.auto_lock_spin.setRange(0, 120)
        self.auto_lock_spin.setSuffix(" min")
        self.clipboard_spin = QSpinBox()
        self.clipboard_spin.setObjectName("comboField")
        self.clipboard_spin.setRange(5, 300)
        self.clipboard_spin.setSuffix(" sec")
        self.mask_usernames_checkbox = QCheckBox("Mask usernames in detail view")
        self.mask_usernames_checkbox.setObjectName("checkField")
        pref_form.addRow("Auto-lock", self.auto_lock_spin)
        pref_form.addRow("Clipboard", self.clipboard_spin)
        pref_form.addRow("Privacy", self.mask_usernames_checkbox)
        preferences.layout.addLayout(pref_form)
        save_preferences = QPushButton("Save Preferences")
        save_preferences.setObjectName("primarySmallButton")
        save_preferences.setCursor(Qt.PointingHandCursor)
        save_preferences.clicked.connect(self.save_preferences)
        preferences.layout.addWidget(save_preferences)
        self.preferences_status = QLabel("")
        self.preferences_status.setObjectName("detailNote")
        self.preferences_status.setWordWrap(True)
        preferences.layout.addWidget(self.preferences_status)
        preferences.layout.addStretch(1)
        body.addWidget(preferences, 1, 1)

        destruct = SectionPanel("Self-Destruct", "Optional failed-unlock trigger and manual vault destruction.")
        destruct_form = QFormLayout()
        self.self_destruct_checkbox = QCheckBox("Enable failed-unlock self-destruct")
        self.self_destruct_checkbox.setObjectName("checkField")
        self.self_destruct_attempts_spin = QSpinBox()
        self.self_destruct_attempts_spin.setObjectName("comboField")
        self.self_destruct_attempts_spin.setRange(1, 20)
        destruct_form.addRow("Trigger", self.self_destruct_checkbox)
        destruct_form.addRow("Attempts", self.self_destruct_attempts_spin)
        destruct.layout.addLayout(destruct_form)
        save_destruct = QPushButton("Save Controls")
        save_destruct.setObjectName("secondaryButton")
        save_destruct.setCursor(Qt.PointingHandCursor)
        save_destruct.clicked.connect(self.save_self_destruct_settings)
        destroy_now = QPushButton("Destroy Vault")
        destroy_now.setObjectName("dangerButton")
        destroy_now.setCursor(Qt.PointingHandCursor)
        destroy_now.clicked.connect(self.trigger_self_destruct)
        destruct_actions = QHBoxLayout()
        destruct_actions.addWidget(save_destruct)
        destruct_actions.addWidget(destroy_now)
        destruct.layout.addLayout(destruct_actions)
        self.self_destruct_status = QLabel("")
        self.self_destruct_status.setObjectName("detailNote")
        self.self_destruct_status.setWordWrap(True)
        destruct.layout.addWidget(self.self_destruct_status)
        destruct.layout.addStretch(1)
        body.addWidget(destruct, 1, 2)

        layout.addLayout(body, 1)
        return view

    def create_credentials_table(self) -> QTableWidget:
        table = QTableWidget(0, 4)
        table.setObjectName("vaultTable")
        table.setHorizontalHeaderLabels(["Service", "Account", "Folder", "Health"])
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(44)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        return table

    def handle_nav(self, name: str) -> None:
        if name == "Overview":
            self.show_overview()
        elif name == "Vault":
            self.show_vault()
        elif name == "Details":
            self.show_detail()
        elif name == "Generator":
            self.show_generator()
        elif name == "Security":
            self.show_security()
        elif name == "Settings":
            self.show_settings()
        else:
            self.activate_nav(name)
            self.set_session_message(f"{name} workspace is unavailable.")

    def activate_nav(self, name: str) -> None:
        for label, button in self.nav_buttons.items():
            button.setChecked(label == name)

    def show_overview(self) -> None:
        self.activate_nav("Overview")
        self.content_stack.setCurrentWidget(self.overview_view)
        self.set_session_message("Command center ready.")

    def show_vault(self) -> None:
        self.activate_nav("Vault")
        self.content_stack.setCurrentWidget(self.vault_view)
        self.refresh_vault_tables()
        self.set_session_message("Vault view ready.")

    def show_detail(self) -> None:
        self.activate_nav("Details")
        self.content_stack.setCurrentWidget(self.detail_view)
        entry = self.selected_entry()
        if entry is not None:
            self.update_detail(entry)
            self.set_session_message(f"Inspecting {entry.service}.")
        else:
            self.update_detail(None)
            self.set_session_message("No credential selected.")

    def show_add_entry(self) -> None:
        self.prepare_entry_editor()
        self.activate_nav("Vault")
        self.content_stack.setCurrentWidget(self.add_entry_view)
        self.service_field.setFocus()
        self.set_session_message("Add a new credential.")

    def edit_selected_entry(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            self.set_session_message("Select a credential first.")
            return
        self.prepare_entry_editor(entry)
        self.activate_nav("Details")
        self.content_stack.setCurrentWidget(self.add_entry_view)
        self.service_field.setFocus()
        self.set_session_message(f"Editing {entry.service}.")

    def cancel_entry_edit(self) -> None:
        self.editing_entry_id = None
        self.clear_entry_form()
        self.show_vault()

    def prepare_entry_editor(self, entry: CredentialEntry | None = None) -> None:
        self.refresh_entry_options(entry.folder if entry else None, entry.entry_type if entry else None)
        self.editing_entry_id = entry.id if entry else None

        if entry is None:
            self.entry_editor_eyebrow.setText("NEW CREDENTIAL")
            self.entry_editor_title.setText("Add Entry")
            self.entry_editor_subtitle.setText("Capture account details into the encrypted local vault.")
            self.save_entry_button.setText("Save Entry")
            self.clear_entry_form()
            return

        self.entry_editor_eyebrow.setText("EDIT CREDENTIAL")
        self.entry_editor_title.setText("Edit Entry")
        self.entry_editor_subtitle.setText("Update encrypted record fields and custom metadata.")
        self.save_entry_button.setText("Update Entry")
        self.service_field.setText(entry.service)
        self.account_field.setText(entry.account)
        self.username_field.setText(entry.username)
        self.entry_password_field.setText(entry.password)
        self.url_field.setText(entry.url)
        self.notes_field.setPlainText(entry.notes)
        self.folder_combo.setCurrentText(entry.folder)
        self.type_combo.setCurrentText(entry.entry_type)
        self.travel_safe_checkbox.setChecked(entry.favorite)
        self.custom_fields_table.setRowCount(0)
        for name, value in entry.custom_fields.items():
            self.add_custom_field_row(name, value)

    def refresh_entry_options(self, selected_folder: str | None = None, selected_type: str | None = None) -> None:
        if not hasattr(self, "folder_combo"):
            return
        selected_folder = selected_folder or self.folder_combo.currentText()
        selected_type = selected_type or self.type_combo.currentText()
        self.folder_combo.blockSignals(True)
        self.type_combo.blockSignals(True)
        self.folder_combo.clear()
        self.folder_combo.addItems(self.available_folders())
        self.type_combo.clear()
        self.type_combo.addItems(self.available_entry_types())
        if selected_folder:
            self.folder_combo.setCurrentText(selected_folder)
        if selected_type:
            self.type_combo.setCurrentText(selected_type)
        self.folder_combo.blockSignals(False)
        self.type_combo.blockSignals(False)

    def show_generator(self) -> None:
        self.activate_nav("Generator")
        self.content_stack.setCurrentWidget(self.generator_view)
        if not self.generated_password_field.text():
            self.generate_standalone_password()
        self.set_session_message("Generator ready.")

    def show_security(self) -> None:
        self.activate_nav("Security")
        self.refresh_security_controls()
        self.refresh_activity()
        self.refresh_password_health()
        self.content_stack.setCurrentWidget(self.security_view)
        self.set_session_message("Security posture ready.")

    def show_settings(self) -> None:
        self.activate_nav("Settings")
        self.database_path_label.setText(str(self.controller.db_path))
        self.refresh_folder_manager()
        self.refresh_settings_controls()
        self.refresh_travel_mode_status()
        self.content_stack.setCurrentWidget(self.settings_view)
        self.set_session_message("Vault settings ready.")

    def search_from_overview(self) -> None:
        query = self.global_search_input.text().strip()
        self.vault_search_input.setText(query)
        self.show_vault()

    def available_folders(self) -> list[str]:
        folders = self.controller.folders()
        preferred = ["Development", "Infrastructure", "Creative", "Personal", "Finance", "Imported"]
        ordered = [folder for folder in preferred if folder in folders]
        ordered.extend(folder for folder in folders if folder not in ordered)
        return ordered or preferred

    def available_entry_types(self) -> list[str]:
        entry_types = self.controller.entry_types()
        preferred = ["Login", "API Key", "Server", "Database", "SSH Key", "Credit Card", "Secure Note", "AWS Account", "Environment Variables"]
        ordered = [entry_type for entry_type in preferred if entry_type in entry_types]
        ordered.extend(entry_type for entry_type in entry_types if entry_type not in ordered)
        return ordered or preferred

    def folder_counts(self) -> list[tuple[str, int]]:
        folder_order = self.available_folders()
        counts = {folder: 0 for folder in folder_order}
        for entry in self.credentials:
            counts[entry.folder] = counts.get(entry.folder, 0) + 1
        total = len(self.credentials)
        return [("All", total)] + [(folder, counts.get(folder, 0)) for folder in folder_order]

    def set_folder_filter(self, folder: str) -> None:
        self.active_folder = folder or "All"
        self.sync_folder_controls()
        self.refresh_vault_tables()
        self.set_session_message(f"Showing {self.active_folder if self.active_folder != 'All' else 'all folders'}.")

    def sync_folder_controls(self) -> None:
        for name, button in self.folder_chip_buttons.items():
            button.setChecked(name == self.active_folder)
        if hasattr(self, "folder_map"):
            self.folder_map.active_folder = self.active_folder
            self.folder_map.update_active_styles()
            self.folder_map.update()

    def rebuild_folder_filter_controls(self) -> None:
        if not hasattr(self, "folder_filter_row"):
            return
        while self.folder_filter_row.count():
            item = self.folder_filter_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.folder_chip_buttons.clear()
        for label in ["All", *self.available_folders()]:
            button = QPushButton(label)
            button.setObjectName("chipButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, folder=label: self.set_folder_filter(folder))
            self.folder_chip_buttons[label] = button
            self.folder_filter_row.addWidget(button)
        self.folder_filter_row.addStretch(1)
        self.sync_folder_controls()

    def refresh_all(self) -> None:
        self.credentials = self.load_credentials()
        folders = sorted({entry.folder for entry in self.credentials})
        weak_count = len([entry for entry in self.credentials if entry.health == "Weak"])
        self.entries_stat.update_values(str(len(self.credentials)), "Encrypted local records")
        self.folders_stat.update_values(str(len(folders)), "Active folder lanes")
        self.security_stat.update_values("Ready" if weak_count == 0 else "Review", f"{weak_count} weak entries")
        self.storage_stat.update_values("SQLite", "Encrypted at rest")
        self.populate_table(self.overview_table, self.credentials[:5], empty_text="No entries yet. Add your first credential.")
        if hasattr(self, "folder_map"):
            self.folder_map.set_folders(self.folder_counts(), self.active_folder)
        if hasattr(self, "folder_filter_row"):
            self.rebuild_folder_filter_controls()
        if hasattr(self, "folder_manager_table"):
            self.refresh_folder_manager()
        if hasattr(self, "travel_mode_status"):
            self.refresh_travel_mode_status()
        if hasattr(self, "folder_combo"):
            self.refresh_entry_options()
        self.sync_folder_controls()
        self.refresh_vault_tables()
        self.refresh_activity()
        self.refresh_password_health()

    def refresh_vault_tables(self) -> None:
        query = self.vault_search_input.text().strip().lower() if hasattr(self, "vault_search_input") else ""
        entries = [
            entry for entry in self.credentials
            if (self.active_folder == "All" or entry.folder == self.active_folder)
            and (not query or query in entry.searchable_text())
        ]
        self.visible_credentials = entries
        if hasattr(self, "vault_table"):
            self.populate_table(self.vault_table, entries, empty_text="No credentials match this search.")
            if entries:
                self.vault_table.selectRow(0)
                self.update_detail(entries[0])
            else:
                self.update_detail(None)

    def populate_table(self, table: QTableWidget, entries: list[CredentialEntry], empty_text: str) -> None:
        table.clearSpans()
        table.setRowCount(0)
        if not entries:
            table.setRowCount(1)
            table.setSpan(0, 0, 1, 4)
            item = QTableWidgetItem(empty_text)
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(0, 0, item)
            return

        table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [entry.service, entry.account, entry.folder, entry.health]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if column in (4, 5):
                    item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, column, item)

    def on_vault_selection_changed(self) -> None:
        if not hasattr(self, "vault_table"):
            return
        selected = self.vault_table.selectionModel().selectedRows()
        if not selected:
            return
        row = selected[0].row()
        if 0 <= row < len(self.visible_credentials):
            self.update_detail(self.visible_credentials[row])

    def selected_entry(self) -> CredentialEntry | None:
        if self.selected_credential is not None:
            return self.selected_credential
        selected = self.vault_table.selectionModel().selectedRows() if hasattr(self, "vault_table") else []
        if not selected:
            return None
        row = selected[0].row()
        if 0 <= row < len(self.visible_credentials):
            return self.visible_credentials[row]
        return None

    def update_detail(self, entry: CredentialEntry | None) -> None:
        self.selected_credential = entry
        if entry is None:
            self.detail_service.setText("No credential selected")
            self.detail_account.setText("Awaiting selected vault record.")
            self.detail_url.setText("")
            self.detail_username.setText("")
            self.detail_password.setText("")
            self.detail_custom_fields.setText("")
            self.detail_notes.setText("")
            if hasattr(self, "detail_context"):
                self.detail_context.setText("No active record")
            return
        self.detail_service.setText(entry.service)
        self.detail_account.setText(f"{entry.account} - {entry.folder} / {entry.entry_type}")
        self.detail_url.setText(f"URL: {entry.url or 'Not set'}")
        username = "******" if self.mask_usernames and entry.username else (entry.username or "Not set")
        self.detail_username.setText(f"User: {username}")
        self.detail_password.setText(f"Password: {entry.masked_password}")
        if entry.custom_fields:
            custom_summary = ", ".join(entry.custom_fields.keys())
            self.detail_custom_fields.setText(f"Custom fields: {custom_summary}")
        else:
            self.detail_custom_fields.setText("Custom fields: None")
        self.detail_notes.setText(entry.notes or "No notes stored for this entry.")
        if hasattr(self, "detail_context"):
            travel_state = "Travel safe" if entry.favorite else "Sensitive"
            self.detail_context.setText(f"{entry.service}\n{entry.folder} / {entry.health} / {travel_state}\nUpdated {entry.updated}")

    def copy_selected_value(self, field: str) -> None:
        entry = self.selected_entry()
        if entry is None:
            self.set_session_message("Select a credential first.")
            return
        value = entry.username if field == "username" else entry.password
        label = "username" if field == "username" else "password"
        self.clipboard.copy(value, on_clear=lambda: self.set_session_message("Clipboard cleared."))
        self.set_session_message(f"Copied {label} for {entry.service}. Clipboard clears in 30 seconds.")

    def generate_entry_password(self) -> None:
        generated = self.make_password()
        self.entry_password_field.setText(generated)
        self.set_session_message("Generated a strong password.")

    def generate_standalone_password(self) -> None:
        self.generated_password_field.setText(self.make_password())
        self.set_session_message("Generated a strong password.")

    def copy_generated_password(self) -> None:
        value = self.generated_password_field.text()
        if not value:
            self.generate_standalone_password()
            value = self.generated_password_field.text()
        self.clipboard.copy(value, on_clear=lambda: self.set_session_message("Clipboard cleared."))
        self.set_session_message("Generated password copied. Clipboard clears in 30 seconds.")

    def use_generated_password(self) -> None:
        value = self.generated_password_field.text()
        if not value:
            self.generate_standalone_password()
            value = self.generated_password_field.text()
        self.show_add_entry()
        self.entry_password_field.setText(value)

    def make_password(self, length: int = 24) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(length))
            if (
                any(char.islower() for char in password)
                and any(char.isupper() for char in password)
                and any(char.isdigit() for char in password)
                and any(char in "!@#$%^&*()-_=+[]{}" for char in password)
            ):
                return password

    def add_custom_field_row(self, name: str = "", value: str = "") -> None:
        row = self.custom_fields_table.rowCount()
        self.custom_fields_table.insertRow(row)
        self.custom_fields_table.setItem(row, 0, QTableWidgetItem(name))
        self.custom_fields_table.setItem(row, 1, QTableWidgetItem(value))
        self.custom_fields_table.selectRow(row)

    def remove_selected_custom_field(self) -> None:
        selected = self.custom_fields_table.selectionModel().selectedRows()
        if selected:
            self.custom_fields_table.removeRow(selected[0].row())

    def custom_fields_from_table(self) -> dict[str, str]:
        fields: dict[str, str] = {}
        for row in range(self.custom_fields_table.rowCount()):
            name_item = self.custom_fields_table.item(row, 0)
            value_item = self.custom_fields_table.item(row, 1)
            name = name_item.text().strip() if name_item else ""
            value = value_item.text() if value_item else ""
            if name:
                fields[name] = value
        return fields

    def save_entry(self) -> None:
        service = self.service_field.text().strip()
        account = self.account_field.text().strip()
        password = self.entry_password_field.text()
        if not service or not account or not password:
            self.set_session_message("Service, account, and password are required.")
            return

        entry = CredentialEntry(
            service=service,
            account=account,
            username=self.username_field.text().strip(),
            password=password,
            url=self.url_field.text().strip(),
            folder=self.folder_combo.currentText(),
            entry_type=self.type_combo.currentText(),
            notes=self.notes_field.toPlainText().strip(),
            health=self.calculate_health(password),
            updated=datetime.now().strftime("%b %d"),
            id=self.editing_entry_id,
            custom_fields=self.custom_fields_from_table(),
            favorite=self.travel_safe_checkbox.isChecked(),
        )
        if self.editing_entry_id is None:
            self.controller.add_entry(entry)
            message = f"Added {entry.service} to the encrypted vault."
        else:
            self.controller.update_entry(self.editing_entry_id, entry)
            message = f"Updated {entry.service}."
        self.clear_entry_form()
        self.editing_entry_id = None
        self.active_folder = entry.folder
        if hasattr(self, "vault_search_input"):
            self.vault_search_input.clear()
        self.refresh_all()
        self.show_vault()
        self.set_session_message(message)

    def delete_selected_entry(self) -> None:
        entry = self.selected_entry()
        if entry is None or entry.id is None:
            self.set_session_message("Select a credential first.")
            return
        answer = QMessageBox.question(
            self,
            "Delete Credential",
            f"Delete {entry.service}? This removes the encrypted record from this vault.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.controller.delete_entry(entry.id)
        except Exception as exc:
            QMessageBox.warning(self, "Delete Failed", str(exc))
            return
        self.selected_credential = None
        self.refresh_all()
        self.show_vault()
        self.set_session_message(f"Deleted {entry.service}.")

    def clear_entry_form(self) -> None:
        for field in [self.service_field, self.account_field, self.username_field, self.entry_password_field, self.url_field]:
            field.clear()
        self.folder_combo.setCurrentIndex(0)
        self.type_combo.setCurrentIndex(0)
        self.travel_safe_checkbox.setChecked(False)
        self.notes_field.clear()
        if hasattr(self, "custom_fields_table"):
            self.custom_fields_table.setRowCount(0)

    def calculate_health(self, password: str) -> str:
        if len(password) >= 16:
            return "Strong"
        if len(password) >= 10:
            return "Good"
        return "Weak"

    def refresh_folder_manager(self) -> None:
        if not hasattr(self, "folder_manager_table"):
            return
        folders = self.available_folders()
        self.folder_manager_table.setRowCount(len(folders))
        for row, folder in enumerate(folders):
            self.folder_manager_table.setItem(row, 0, QTableWidgetItem(folder))

    def selected_folder_name(self) -> str | None:
        selected = self.folder_manager_table.selectionModel().selectedRows() if hasattr(self, "folder_manager_table") else []
        if not selected:
            return None
        item = self.folder_manager_table.item(selected[0].row(), 0)
        return item.text() if item else None

    def add_folder(self) -> None:
        name, accepted = QInputDialog.getText(self, "Add Folder", "Folder name")
        if not accepted:
            return
        try:
            self.controller.add_folder(name)
        except Exception as exc:
            QMessageBox.warning(self, "Folder Not Added", str(exc))
            return
        self.refresh_all()
        self.folder_manager_status.setText(f"Added folder {name.strip()}.")
        self.set_session_message(f"Added folder {name.strip()}.")

    def rename_selected_folder(self) -> None:
        folder = self.selected_folder_name()
        if not folder:
            self.set_session_message("Select a folder first.")
            return
        name, accepted = QInputDialog.getText(self, "Rename Folder", "Folder name", text=folder)
        if not accepted:
            return
        try:
            self.controller.rename_folder(folder, name)
        except Exception as exc:
            QMessageBox.warning(self, "Folder Not Renamed", str(exc))
            return
        if self.active_folder == folder:
            self.active_folder = name.strip()
        self.refresh_all()
        self.folder_manager_status.setText(f"Renamed {folder} to {name.strip()}.")
        self.set_session_message(f"Renamed folder {folder}.")

    def delete_selected_folder(self) -> None:
        folder = self.selected_folder_name()
        if not folder:
            self.set_session_message("Select a folder first.")
            return
        answer = QMessageBox.question(
            self,
            "Delete Folder",
            f"Delete {folder}? Existing records will move to Imported.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.controller.delete_folder(folder)
        except Exception as exc:
            QMessageBox.warning(self, "Folder Not Deleted", str(exc))
            return
        if self.active_folder == folder:
            self.active_folder = "Imported"
        self.refresh_all()
        self.folder_manager_status.setText(f"Deleted {folder}; records moved to Imported.")
        self.set_session_message(f"Deleted folder {folder}.")

    def refresh_settings_controls(self) -> None:
        if not hasattr(self, "auto_lock_spin"):
            return
        self.auto_lock_minutes = self.controller.setting_int("auto_lock_minutes", self.auto_lock_minutes)
        self.clipboard_clear_seconds = self.controller.setting_int("clipboard_clear_seconds", self.clipboard_clear_seconds)
        self.mask_usernames = self.controller.setting_bool("mask_usernames", self.mask_usernames)
        self.auto_lock_spin.setValue(self.auto_lock_minutes)
        self.clipboard_spin.setValue(self.clipboard_clear_seconds)
        self.mask_usernames_checkbox.setChecked(self.mask_usernames)
        self.self_destruct_checkbox.setChecked(self.controller.setting_bool("self_destruct_enabled", False))
        self.self_destruct_attempts_spin.setValue(self.controller.setting_int("self_destruct_failed_attempts", 5))
        self.preferences_status.setText(f"Auto-lock {self.auto_lock_minutes} min; clipboard {self.clipboard_clear_seconds} sec.")
        self.self_destruct_status.setText("Disabled" if not self.self_destruct_checkbox.isChecked() else "Failed-unlock trigger enabled.")

    def save_preferences(self) -> None:
        self.auto_lock_minutes = self.auto_lock_spin.value()
        self.clipboard_clear_seconds = self.clipboard_spin.value()
        self.mask_usernames = self.mask_usernames_checkbox.isChecked()
        self.controller.set_setting("auto_lock_minutes", self.auto_lock_minutes)
        self.controller.set_setting("clipboard_clear_seconds", self.clipboard_clear_seconds)
        self.controller.set_setting("mask_usernames", self.mask_usernames)
        self.clipboard.clear_after_ms = self.clipboard_clear_seconds * 1000
        self.restart_auto_lock_timer()
        self.refresh_security_controls()
        self.refresh_vault_tables()
        self.preferences_status.setText("Preferences saved.")
        self.set_session_message("Preferences saved.")

    def save_self_destruct_settings(self) -> None:
        enabled = self.self_destruct_checkbox.isChecked()
        attempts = self.self_destruct_attempts_spin.value()
        self.controller.set_setting("self_destruct_enabled", enabled)
        self.controller.set_setting("self_destruct_failed_attempts", attempts)
        self.self_destruct_status.setText(f"Enabled after {attempts} failed unlock attempts." if enabled else "Disabled.")
        self.set_session_message("Self-destruct controls saved.")

    def refresh_travel_mode_status(self) -> None:
        if not hasattr(self, "travel_mode_status"):
            return
        active = self.controller.is_travel_mode_active()
        total = len(self.credentials)
        safe = len([entry for entry in self.credentials if entry.favorite])
        removed = self.controller.setting_int("travel_mode_removed_count", 0)
        if active:
            backup = self.controller.travel_mode_backup_path() or "No backup path recorded"
            self.travel_mode_status.setText(f"ACTIVE - {total} records on device, {removed} removed. Backup: {backup}")
        else:
            self.travel_mode_status.setText(f"Inactive - {safe}/{total} records marked travel safe.")

    def restore_entries(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Restore Backup",
            str(default_export_dir()),
            "Vault Backups (*.ratvault *.rattravel *.cvbak *.json);;All Files (*)",
        )
        if not path:
            return
        passphrase, accepted = QInputDialog.getText(
            self,
            "Restore Passphrase",
            "Backup passphrase. Leave blank only for plain JSON.",
            QLineEdit.Password,
        )
        if not accepted:
            return
        answer = QMessageBox.warning(
            self,
            "Restore Backup",
            "Restore will replace the current vault records with the backup contents.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            count = self.controller.restore_path(path, passphrase or None)
        except Exception as exc:
            QMessageBox.warning(self, "Restore Failed", str(exc))
            self.set_session_message("Restore failed.")
            return
        self.refresh_all()
        self.transfer_status.setText(f"Restored {count} entries from {path}.")
        self.set_session_message(f"Restored {count} entries.")

    def activate_travel_mode(self) -> None:
        if self.controller.is_travel_mode_active():
            self.set_session_message("Travel mode is already active.")
            return
        default_path = default_export_dir() / f"rat-travel-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.rattravel"
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Travel Backup",
            str(default_path),
            "Rat Travel Backup (*.rattravel);;Rat Vault Backup (*.ratvault);;All Files (*)",
        )
        if not path:
            return
        if not path.endswith((".rattravel", ".ratvault")):
            path = f"{path}.rattravel"
        passphrase = self.request_export_passphrase(
            title="Travel Backup Passphrase",
            prompt="Choose and confirm the passphrase for the full travel backup.",
        )
        if passphrase is None:
            return
        total = len(self.credentials)
        safe = len([entry for entry in self.credentials if entry.favorite])
        answer = QMessageBox.warning(
            self,
            "Activate Travel Mode",
            f"This will create an encrypted backup, keep {safe} travel-safe records, and remove {total - safe} records from this device.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            result = self.controller.activate_travel_mode(path, passphrase)
        except Exception as exc:
            QMessageBox.warning(self, "Travel Mode Failed", str(exc))
            return
        self.refresh_all()
        self.refresh_travel_mode_status()
        self.set_session_message(f"Travel mode active. Removed {result['removed']} records.")

    def restore_travel_mode(self) -> None:
        path = self.controller.travel_mode_backup_path()
        if not path or not Path(path).exists():
            selected, _selected_filter = QFileDialog.getOpenFileName(
                self,
                "Open Travel Backup",
                str(default_export_dir()),
                "Rat Travel Backup (*.rattravel *.ratvault);;All Files (*)",
            )
            path = selected
        if not path:
            return
        passphrase, accepted = QInputDialog.getText(
            self,
            "Travel Backup Passphrase",
            "Passphrase for the travel backup.",
            QLineEdit.Password,
        )
        if not accepted:
            return
        answer = QMessageBox.question(
            self,
            "Restore Travel Backup",
            "Restore the full vault from the travel backup and disable Travel Mode?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            count = self.controller.deactivate_travel_mode(path, passphrase)
        except Exception as exc:
            QMessageBox.warning(self, "Travel Restore Failed", str(exc))
            return
        self.refresh_all()
        self.refresh_travel_mode_status()
        self.set_session_message(f"Travel mode restored {count} entries.")

    def trigger_self_destruct(self) -> None:
        answer = QMessageBox.critical(
            self,
            "Destroy Vault",
            "This permanently removes the local encrypted vault database from this machine.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        phrase, accepted = QInputDialog.getText(
            self,
            "Final Confirmation",
            "Type DESTROY RAT VAULT to confirm.",
        )
        if not accepted or phrase != "DESTROY RAT VAULT":
            self.set_session_message("Self-destruct cancelled.")
            return
        success, message = self.controller.self_destruct()
        if success:
            QMessageBox.information(self, "Vault Destroyed", message)
            QApplication.instance().quit()
        else:
            QMessageBox.warning(self, "Self-Destruct Failed", message)

    def import_entries_from_file(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Import Credentials",
            str(default_export_dir()),
            "Vault Imports (*.ratvault *.cvbak *.json *.csv);;All Files (*)",
        )
        if path:
            self.import_entries_from_path(path)

    def import_entries_from_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Import Credential Folder", str(default_export_dir()))
        if path:
            self.import_entries_from_path(path)

    def import_entries_from_path(self, path: str) -> None:
        passphrase, accepted = QInputDialog.getText(
            self,
            "Import Passphrase",
            "Import passphrase for encrypted Rat/Kitty backups. Leave blank for plain CSV or JSON.",
            QLineEdit.Password,
        )
        if not accepted:
            return
        try:
            count = self.controller.import_path(path, passphrase=passphrase or None)
        except Exception as exc:
            QMessageBox.warning(self, "Import Failed", str(exc))
            self.set_session_message("Import failed.")
            return
        self.refresh_all()
        self.transfer_status.setText(f"Imported {count} entries from {path}.")
        self.set_session_message(f"Imported {count} entries.")

    def export_entries(self) -> None:
        default_path = default_export_dir() / f"rat-vault-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.ratvault"
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Encrypted Backup",
            str(default_path),
            "Rat Vault Backup (*.ratvault);;All Files (*)",
        )
        if not path:
            return
        if not path.endswith(".ratvault"):
            path = f"{path}.ratvault"

        passphrase = self.request_export_passphrase()
        if passphrase is None:
            return

        try:
            count = self.controller.export_path(path, passphrase)
        except Exception as exc:
            QMessageBox.warning(self, "Export Failed", str(exc))
            self.set_session_message("Export failed.")
            return
        self.transfer_status.setText(f"Exported {count} entries to {path}.")
        self.refresh_activity()
        self.set_session_message(f"Exported {count} entries.")

    def request_export_passphrase(
        self,
        title: str = "Export Passphrase",
        prompt: str = "Choose and confirm an export passphrase for this encrypted backup.",
    ) -> str | None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        prompt_label = QLabel(prompt)
        prompt_label.setWordWrap(True)
        layout.addWidget(prompt_label)

        form = QFormLayout()
        passphrase_input = QLineEdit()
        passphrase_input.setEchoMode(QLineEdit.Password)
        passphrase_input.setObjectName("formField")
        confirm_input = QLineEdit()
        confirm_input.setEchoMode(QLineEdit.Password)
        confirm_input.setObjectName("formField")
        form.addRow("Passphrase", passphrase_input)
        form.addRow("Confirm", confirm_input)
        layout.addLayout(form)

        status = QLabel("")
        status.setObjectName("statusLabel")
        status.setWordWrap(True)
        layout.addWidget(status)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        def validate() -> None:
            passphrase = passphrase_input.text()
            confirm = confirm_input.text()
            if len(passphrase) < 12:
                status.setText("Use at least 12 characters.")
                return
            if passphrase != confirm:
                status.setText("Passphrases do not match.")
                return
            dialog.accept()

        buttons.accepted.connect(validate)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec_() != QDialog.Accepted:
            return None
        return passphrase_input.text()

    def run_breach_check(self) -> None:
        if self.breach_worker is not None and self.breach_worker.isRunning():
            self.set_session_message("Breach check already running.")
            return
        entries = self.controller.list_entries()
        self.breach_worker = BreachCheckWorker(entries)
        self.breach_worker.progress_update.connect(self.on_breach_progress)
        self.breach_worker.check_complete.connect(self.on_breach_complete)
        self.breach_worker.finished.connect(self.on_breach_finished)
        if hasattr(self, "security_rows"):
            self.security_rows["Breach checks"].setText("Running...")
        self.set_session_message("Running breach check in the background.")
        self.breach_worker.start()

    def on_breach_progress(self, current: int, total: int) -> None:
        if hasattr(self, "security_rows"):
            self.security_rows["Breach checks"].setText(f"Checking {current}/{total}")
        self.set_session_message(f"Breach check {current}/{total}.")

    def on_breach_complete(self, result: str) -> None:
        if hasattr(self, "security_rows"):
            self.security_rows["Breach checks"].setText(result)
        self.set_session_message(result)

    def on_breach_finished(self) -> None:
        self.breach_worker = None
        self.refresh_activity()

    def refresh_security_controls(self) -> None:
        if not hasattr(self, "security_rows"):
            return
        self.security_rows["Clipboard"].setText(f"Auto-clear after {self.clipboard_clear_seconds} seconds")
        self.security_rows["Auto-lock"].setText("Disabled" if self.auto_lock_minutes == 0 else f"{self.auto_lock_minutes} minutes")
        travel_state = "Active" if self.controller.is_travel_mode_active() else "Inactive"
        if "Travel mode" in self.security_rows:
            self.security_rows["Travel mode"].setText(travel_state)

    def refresh_password_health(self) -> None:
        if not hasattr(self, "health_table") or not self.controller.unlocked:
            return
        report = self.controller.password_health_report()
        self.health_total_label.setText(f"{report['total']} entries")
        self.health_strong_label.setText(f"{report['strong']} strong")
        self.health_review_label.setText(f"{report['review']} review")
        self.health_weak_label.setText(f"{report['weak']} weak")

        rows = report["rows"]
        self.health_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [row["service"], row["folder"], row["status"], row["issues"]]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.health_table.setItem(row_index, column, item)

    def refresh_activity(self) -> None:
        if not hasattr(self, "activity_labels"):
            return
        activity = self.controller.recent_activity()
        for index, label in enumerate(self.activity_labels):
            if index < len(activity):
                item = activity[index]
                label.setText(f"{item['created_at']}  {item['action']}  {item['description']}")
                label.show()
            else:
                label.setText("No additional activity.")
                label.show()

    def handle_auto_lock(self) -> None:
        self.auto_lock_timer.stop()
        if hasattr(self, "session_status"):
            self.session_status.setText("Auto-lock engaged after inactivity.")
        self.on_lock()

    def restart_auto_lock_timer(self) -> None:
        if not hasattr(self, "auto_lock_timer"):
            return
        self.auto_lock_timer.stop()
        if self.auto_lock_minutes > 0:
            self.auto_lock_timer.start(self.auto_lock_minutes * 60 * 1000)

    def set_session_message(self, message: str) -> None:
        if hasattr(self, "session_status"):
            self.session_status.setText(message)
        self.restart_auto_lock_timer()


class PortalWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.drag_position = QPoint()
        self.mode = "unlock"
        self.transient_secret = bytearray()
        self.controller = VaultController()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1180, 740)
        self.resize(1280, 780)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.build_ui()
        self.fade_in()

    def build_ui(self) -> None:
        self.backdrop = RatModeBackdrop(self)
        root = QStackedLayout(self)
        root.setStackingMode(QStackedLayout.StackAll)
        root.addWidget(self.backdrop)

        surface = QWidget()
        surface.setObjectName("surface")
        root.addWidget(surface)
        root.setCurrentWidget(surface)

        layout = QVBoxLayout(surface)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(0)

        layout.addWidget(self.build_topbar())

        self.view_host = QWidget()
        self.view_stack = QStackedLayout(self.view_host)
        self.view_stack.setContentsMargins(0, 0, 0, 0)
        self.view_stack.addWidget(self.build_login_view())
        self.dashboard_view = DashboardWidget(self.lock_to_portal, self.controller)
        self.view_stack.addWidget(self.dashboard_view)
        layout.addWidget(self.view_host, 1)

        self.setStyleSheet(self.stylesheet())

    def build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        mark = QLabel("RAT MODE")
        mark.setObjectName("topMark")
        row.addWidget(mark)

        self.top_status = QLabel("LOCAL PORTAL")
        self.top_status.setObjectName("topStatus")
        row.addWidget(self.top_status)
        row.addStretch(1)

        self.minimize_button = QPushButton("-")
        self.minimize_button.setObjectName("windowButton")
        self.minimize_button.clicked.connect(self.showMinimized)
        self.close_button = QPushButton("x")
        self.close_button.setObjectName("windowButtonDanger")
        self.close_button.clicked.connect(self.close)
        row.addWidget(self.minimize_button)
        row.addWidget(self.close_button)
        return bar

    def build_login_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(1)

        body = QHBoxLayout()
        body.setContentsMargins(28, 0, 28, 20)
        body.setSpacing(0)
        body.addWidget(self.build_panel())
        body.addStretch(1)
        layout.addLayout(body)
        layout.addStretch(1)
        return view

    def build_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("loginPanel")
        panel.setFixedWidth(430)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(34, 32, 34, 32)
        panel_layout.setSpacing(18)

        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setColor(QColor(255, 63, 145, 55))
        shadow.setBlurRadius(38)
        shadow.setOffset(0, 0)
        panel.setGraphicsEffect(shadow)

        title_row = QHBoxLayout()
        title_row.setSpacing(14)
        title_row.addWidget(RatSeal())

        title_stack = QVBoxLayout()
        title_stack.setSpacing(1)
        title = QLabel("Coding Rat Vault")
        title.setObjectName("title")
        subtitle = QLabel("Night-shift credential control")
        subtitle.setObjectName("subtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        title_row.addLayout(title_stack)
        title_row.addStretch(1)
        panel_layout.addLayout(title_row)

        self.mode_group = QButtonGroup(self)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self.unlock_mode_button = ModeButton("Unlock")
        self.unlock_mode_button.setObjectName("modeButton")
        self.create_mode_button = ModeButton("Create")
        self.create_mode_button.setObjectName("modeButton")
        self.mode_group.addButton(self.unlock_mode_button)
        self.mode_group.addButton(self.create_mode_button)
        self.unlock_mode_button.setChecked(True)
        self.unlock_mode_button.clicked.connect(lambda: self.set_mode("unlock"))
        self.create_mode_button.clicked.connect(lambda: self.set_mode("create"))
        mode_row.addWidget(self.unlock_mode_button)
        mode_row.addWidget(self.create_mode_button)
        panel_layout.addLayout(mode_row)

        self.access_id_input = QLineEdit()
        self.access_id_input.setObjectName("field")
        self.access_id_input.setPlaceholderText("Access ID")
        self.access_id_input.returnPressed.connect(self.submit)
        panel_layout.addWidget(self.access_id_input)

        self.passphrase_input = QLineEdit()
        self.passphrase_input.setObjectName("field")
        self.passphrase_input.setEchoMode(QLineEdit.Password)
        self.passphrase_input.setPlaceholderText("Master passphrase")
        self.passphrase_input.returnPressed.connect(self.submit)
        panel_layout.addWidget(self.passphrase_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setObjectName("field")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Confirm passphrase")
        self.confirm_input.returnPressed.connect(self.submit)
        self.confirm_input.hide()
        panel_layout.addWidget(self.confirm_input)

        aux_row = QHBoxLayout()
        aux_row.setSpacing(8)
        self.reveal_button = QPushButton("Show")
        self.reveal_button.setObjectName("ghostButton")
        self.reveal_button.setCheckable(True)
        self.reveal_button.clicked.connect(self.toggle_secret_visibility)
        aux_row.addWidget(self.reveal_button)
        self.demo_button = QPushButton("Fill Demo")
        self.demo_button.setObjectName("ghostButton")
        self.demo_button.setCursor(Qt.PointingHandCursor)
        self.demo_button.clicked.connect(self.fill_demo_account)
        aux_row.addWidget(self.demo_button)
        aux_row.addStretch(1)
        self.mode_hint = QLabel("Encrypted local vault")
        self.mode_hint.setObjectName("hint")
        aux_row.addWidget(self.mode_hint)
        panel_layout.addLayout(aux_row)

        self.submit_button = QPushButton("Unlock Vault")
        self.submit_button.setObjectName("primaryButton")
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.clicked.connect(self.submit)
        panel_layout.addWidget(self.submit_button)

        self.status_label = QLabel("Create or unlock the encrypted local vault")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        panel_layout.addWidget(self.status_label)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        panel_layout.addWidget(divider)

        telemetry = QHBoxLayout()
        telemetry.setSpacing(10)
        telemetry.addWidget(self.small_metric("mode", "rat"))
        telemetry.addWidget(self.small_metric("store", "local"))
        telemetry.addWidget(self.small_metric("state", "sealed"))
        panel_layout.addLayout(telemetry)

        self.set_mode("unlock")
        return panel

    def small_metric(self, label: str, value: str) -> QWidget:
        box = QFrame()
        box.setObjectName("metric")
        column = QVBoxLayout(box)
        column.setContentsMargins(10, 8, 10, 8)
        column.setSpacing(0)
        label_widget = QLabel(label.upper())
        label_widget.setObjectName("metricLabel")
        value_widget = QLabel(value.upper())
        value_widget.setObjectName("metricValue")
        column.addWidget(label_widget)
        column.addWidget(value_widget)
        return box

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        is_create = mode == "create"
        self.confirm_input.setVisible(is_create)
        self.submit_button.setText("Create Vault" if is_create else "Unlock Vault")
        self.access_id_input.setPlaceholderText("New access ID" if is_create else "Access ID")
        self.mode_hint.setText("New encrypted vault" if is_create else "Encrypted local vault")
        if is_create:
            self.status_label.setText("Choose an access ID and master passphrase")
        elif self.controller.vault_exists():
            self.status_label.setText("Unlock the local encrypted vault")
        else:
            self.status_label.setText("Create a vault first, or use Fill Demo")
        self.access_id_input.setFocus()

    def toggle_secret_visibility(self) -> None:
        visible = self.reveal_button.isChecked()
        mode = QLineEdit.Normal if visible else QLineEdit.Password
        self.passphrase_input.setEchoMode(mode)
        self.confirm_input.setEchoMode(mode)
        self.reveal_button.setText("Hide" if visible else "Show")

    def fill_demo_account(self) -> None:
        self.set_mode("unlock")
        self.unlock_mode_button.setChecked(True)
        self.access_id_input.setText(DEMO_ACCESS_ID)
        self.passphrase_input.setText(DEMO_PASSPHRASE)
        self.status_label.setText("Demo credentials loaded")
        self.passphrase_input.setFocus()

    def is_demo_credentials(self, access_id: str, secret: str) -> bool:
        return access_id.strip().lower() == DEMO_ACCESS_ID and secret == DEMO_PASSPHRASE

    def unlock_demo_vault(self) -> str:
        demo_controller = VaultController(demo_vault_db_path())
        if not demo_controller.vault_exists():
            demo_controller.create_vault(DEMO_ACCESS_ID, DEMO_PASSPHRASE)
        else:
            demo_controller.unlock_vault(DEMO_ACCESS_ID, DEMO_PASSPHRASE)
        self.seed_demo_entries(demo_controller)
        self.controller = demo_controller
        self.dashboard_view.set_controller(self.controller)
        return f"Demo vault unlocked at {self.controller.db_path}."

    def seed_demo_entries(self, controller: VaultController) -> None:
        if controller.list_entries():
            return
        demo_entries = [
            CredentialEntry(
                service="GitHub Workspace",
                account="theRadicalSoftware",
                username="rat@vault.local",
                password="demo-github-pass-2026",
                url="https://github.com/theRadicalSoftware",
                folder="Development",
                entry_type="Login",
                notes="Public demo credential for UI and workflow testing only.",
                health="Strong",
                favorite=True,
            ),
            CredentialEntry(
                service="Deploy Console",
                account="Rat Mode Sandbox",
                username="deploy@rat.local",
                password="sandbox-deploy-pass-2026",
                url="https://deploy.example.local",
                folder="Infrastructure",
                entry_type="Server",
                notes="Demo server record. No production system is connected.",
                health="Strong",
            ),
            CredentialEntry(
                service="Design Vault",
                account="Brand Assets",
                username="design@rat.local",
                password="brand-demo-pass",
                url="https://assets.example.local",
                folder="Creative",
                entry_type="Secure Note",
                notes="Placeholder for brand asset access details.",
                health="Good",
            ),
        ]
        for entry in demo_entries:
            controller.add_entry(entry)

    def submit(self) -> None:
        self.clear_transient_secret()
        access_id = self.access_id_input.text().strip()
        secret = self.passphrase_input.text()
        confirm = self.confirm_input.text()
        self.transient_secret = bytearray(secret.encode("utf-8"))

        if not access_id:
            self.status_label.setText("Access ID required")
            self.clear_transient_secret()
            self.shake_panel()
            return

        if not secret:
            self.status_label.setText("Master key required")
            self.clear_transient_secret()
            self.shake_panel()
            return

        if self.mode == "create":
            if len(secret) < 12:
                self.status_label.setText("Use at least 12 characters")
                self.clear_transient_secret()
                self.shake_panel()
                return
            if secret != confirm:
                self.status_label.setText("Confirmation does not match")
                self.clear_transient_secret()
                self.shake_panel()
                return
            try:
                message = self.controller.create_vault(access_id, secret)
            except Exception as exc:
                self.status_label.setText(str(exc))
                self.clear_transient_secret()
                self.shake_panel()
                return
        else:
            if self.is_demo_credentials(access_id, secret):
                try:
                    message = self.unlock_demo_vault()
                except Exception as exc:
                    self.status_label.setText(str(exc))
                    self.clear_transient_secret()
                    self.shake_panel()
                    return
                self.clear_transient_secret()
                self.access_id_input.clear()
                self.passphrase_input.clear()
                self.confirm_input.clear()
                self.show_dashboard(message)
                return
            if not self.controller.vault_exists():
                self.status_label.setText("No local vault exists yet. Switch to Create.")
                self.clear_transient_secret()
                self.shake_panel()
                return
            try:
                message = self.controller.unlock_vault(access_id, secret)
            except Exception as exc:
                should_destroy = False
                try:
                    should_destroy = self.controller.register_failed_unlock()
                except Exception:
                    pass
                if should_destroy:
                    success, destroy_message = self.controller.self_destruct()
                    self.status_label.setText(destroy_message if success else str(exc))
                    self.clear_transient_secret()
                    QMessageBox.critical(self, "Vault Destroyed", destroy_message)
                    QApplication.instance().quit()
                    return
                self.status_label.setText(str(exc))
                self.clear_transient_secret()
                self.shake_panel()
                return

        self.clear_transient_secret()
        self.access_id_input.clear()
        self.passphrase_input.clear()
        self.confirm_input.clear()
        self.show_dashboard(message)

    def show_dashboard(self, message: str) -> None:
        self.top_status.setText("VAULT DASHBOARD")
        self.dashboard_view.refresh_all()
        self.dashboard_view.restart_auto_lock_timer()
        self.view_stack.setCurrentWidget(self.dashboard_view)
        self.dashboard_view.set_session_message(message)

    def lock_to_portal(self) -> None:
        self.clear_transient_secret()
        if self.controller.unlocked:
            self.controller.lock()
        self.controller = VaultController()
        self.dashboard_view.set_controller(self.controller)
        if hasattr(self.dashboard_view, "auto_lock_timer"):
            self.dashboard_view.auto_lock_timer.stop()
        self.access_id_input.clear()
        self.passphrase_input.clear()
        self.confirm_input.clear()
        self.top_status.setText("LOCAL PORTAL")
        self.status_label.setText("Vault locked")
        self.view_stack.setCurrentIndex(0)
        self.access_id_input.setFocus()

    def clear_transient_secret(self) -> None:
        for i in range(len(self.transient_secret)):
            self.transient_secret[i] = 0
        self.transient_secret.clear()

    def shake_panel(self) -> None:
        panel = self.findChild(QFrame, "loginPanel")
        if panel is None:
            return
        start = panel.pos()
        animation = QPropertyAnimation(panel, b"pos", self)
        animation.setDuration(180)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.setKeyValueAt(0.0, start)
        animation.setKeyValueAt(0.25, start + QPoint(-8, 0))
        animation.setKeyValueAt(0.5, start + QPoint(8, 0))
        animation.setKeyValueAt(0.75, start + QPoint(-4, 0))
        animation.setKeyValueAt(1.0, start)
        animation.start(QPropertyAnimation.DeleteWhenStopped)

    def fade_in(self) -> None:
        self.setWindowOpacity(0.0)
        animation = QPropertyAnimation(self, b"windowOpacity", self)
        animation.setDuration(260)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start(QPropertyAnimation.DeleteWhenStopped)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.backdrop.resize(self.size())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and event.pos().y() <= 58:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.drag_position = QPoint()
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        self.clear_transient_secret()
        if self.controller.unlocked:
            self.controller.lock()
        self.access_id_input.clear()
        self.passphrase_input.clear()
        self.confirm_input.clear()
        super().closeEvent(event)

    def stylesheet(self) -> str:
        return f"""
            QWidget {{
                color: {TEXT};
                font-family: "Inter", "Segoe UI", "DejaVu Sans", sans-serif;
                letter-spacing: 0px;
            }}
            QLabel#topMark {{
                color: {MAGENTA_SOFT};
                font-size: 12px;
                font-weight: 700;
                padding: 8px 12px;
                border: 1px solid rgba(255, 63, 145, 92);
                background: rgba(10, 11, 15, 150);
                border-radius: 6px;
            }}
            QLabel#topStatus {{
                color: rgba(230, 232, 238, 165);
                font-size: 11px;
                padding: 8px 10px;
            }}
            QPushButton#windowButton,
            QPushButton#windowButtonDanger {{
                min-width: 32px;
                max-width: 32px;
                min-height: 28px;
                max-height: 28px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 700;
                background: rgba(17, 18, 24, 168);
                border: 1px solid rgba(255, 255, 255, 34);
                color: rgba(241, 243, 248, 178);
            }}
            QPushButton#windowButton:hover {{
                border-color: rgba(255, 63, 145, 135);
                color: {TEXT};
            }}
            QPushButton#windowButtonDanger:hover {{
                background: rgba(255, 63, 145, 76);
                border-color: rgba(255, 63, 145, 155);
                color: white;
            }}
            QFrame#loginPanel {{
                background: rgba(8, 9, 13, 224);
                border: 1px solid rgba(255, 63, 145, 82);
                border-radius: 8px;
            }}
            QFrame#sidebar {{
                background: rgba(8, 9, 13, 218);
                border: 1px solid rgba(255, 255, 255, 24);
                border-radius: 8px;
            }}
            QLabel#sidebarTitle {{
                color: {TEXT};
                font-size: 18px;
                font-weight: 780;
            }}
            QLabel#sidebarSubtle {{
                color: rgba(255, 106, 169, 175);
                font-size: 11px;
            }}
            QPushButton#navButton {{
                background: rgba(17, 19, 25, 112);
                border: 1px solid rgba(255, 255, 255, 24);
                border-radius: 7px;
                color: rgba(241, 243, 248, 178);
                font-size: 13px;
                font-weight: 650;
                text-align: left;
                padding-left: 14px;
            }}
            QPushButton#navButton:hover {{
                background: rgba(28, 30, 38, 150);
                border-color: rgba(255, 63, 145, 92);
                color: white;
            }}
            QPushButton#navButton:checked {{
                background: rgba(255, 63, 145, 42);
                border-color: rgba(255, 63, 145, 150);
                color: white;
            }}
            QFrame#sessionBox {{
                background: rgba(255, 255, 255, 14);
                border: 1px solid rgba(255, 255, 255, 24);
                border-radius: 7px;
            }}
            QLabel#sessionState {{
                color: {TEXT};
                font-size: 13px;
                font-weight: 750;
            }}
            QLabel#sessionNote {{
                color: rgba(157, 161, 173, 185);
                font-size: 11px;
            }}
            QLabel#eyebrow {{
                color: {MAGENTA_SOFT};
                font-size: 11px;
                font-weight: 800;
            }}
            QLabel#dashboardTitle {{
                color: {TEXT};
                font-size: 34px;
                font-weight: 820;
            }}
            QLabel#dashboardSubtitle {{
                color: rgba(218, 221, 230, 168);
                font-size: 13px;
            }}
            QLineEdit#dashboardSearch {{
                min-height: 42px;
                border-radius: 7px;
                padding: 0 14px;
                background: rgba(13, 15, 20, 218);
                border: 1px solid rgba(255, 255, 255, 32);
                color: {TEXT};
                font-size: 14px;
                selection-background-color: rgba(255, 63, 145, 110);
            }}
            QLineEdit#dashboardSearch:focus {{
                border-color: rgba(255, 63, 145, 150);
            }}
            QPushButton#primarySmallButton,
            QPushButton#secondaryButton,
            QPushButton#dangerButton {{
                min-height: 42px;
                border-radius: 7px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 800;
            }}
            QPushButton#primarySmallButton {{
                background: rgba(255, 63, 145, 210);
                border: 1px solid rgba(255, 145, 190, 205);
                color: white;
            }}
            QPushButton#primarySmallButton:hover {{
                background: rgba(255, 83, 157, 230);
            }}
            QPushButton#secondaryButton {{
                background: rgba(20, 22, 29, 180);
                border: 1px solid rgba(255, 255, 255, 34);
                color: rgba(241, 243, 248, 190);
            }}
            QPushButton#secondaryButton:hover {{
                border-color: rgba(255, 63, 145, 130);
                color: white;
            }}
            QPushButton#dangerButton {{
                background: rgba(47, 18, 25, 185);
                border: 1px solid rgba(255, 88, 116, 92);
                color: rgba(255, 214, 222, 205);
            }}
            QPushButton#dangerButton:hover {{
                background: rgba(94, 24, 41, 210);
                border-color: rgba(255, 88, 116, 165);
                color: white;
            }}
            QFrame#statCard {{
                background: rgba(9, 10, 14, 205);
                border: 1px solid rgba(255, 255, 255, 24);
                border-radius: 8px;
            }}
            QLabel#statLabel {{
                color: rgba(157, 161, 173, 168);
                font-size: 10px;
                font-weight: 800;
            }}
            QLabel#statValue {{
                color: {TEXT};
                font-size: 24px;
                font-weight: 820;
            }}
            QLabel#statDetail {{
                color: rgba(218, 221, 230, 150);
                font-size: 11px;
            }}
            QFrame#sectionPanel {{
                background: rgba(8, 9, 13, 214);
                border: 1px solid rgba(255, 255, 255, 24);
                border-radius: 8px;
            }}
            QLabel#sectionTitle {{
                color: {TEXT};
                font-size: 18px;
                font-weight: 800;
            }}
            QLabel#sectionSubtitle {{
                color: rgba(157, 161, 173, 180);
                font-size: 12px;
            }}
            QFrame#folderMap {{
                background: rgba(5, 6, 9, 86);
                border: 1px solid rgba(255, 255, 255, 18);
                border-radius: 7px;
            }}
            QPushButton#folderNodeButton {{
                background: rgba(14, 16, 22, 220);
                border: 1px solid rgba(255, 255, 255, 32);
                border-radius: 8px;
                color: rgba(241, 243, 248, 188);
                font-size: 10px;
                font-weight: 760;
                padding: 4px 6px;
            }}
            QPushButton#folderNodeButton:hover {{
                background: rgba(30, 33, 42, 226);
                border-color: rgba(255, 63, 145, 128);
                color: white;
            }}
            QPushButton#folderNodeButton:checked {{
                background: rgba(255, 63, 145, 56);
                border-color: rgba(255, 63, 145, 176);
                color: white;
            }}
            QPushButton#chipButton {{
                min-height: 28px;
                padding: 0 12px;
                background: rgba(17, 19, 25, 180);
                border: 1px solid rgba(255, 255, 255, 26);
                color: rgba(241, 243, 248, 170);
                border-radius: 14px;
                font-size: 12px;
            }}
            QPushButton#chipButton:checked {{
                background: rgba(255, 63, 145, 42);
                border-color: rgba(255, 63, 145, 145);
                color: white;
            }}
            QTableWidget#vaultTable {{
                background: rgba(5, 6, 9, 142);
                border: 1px solid rgba(255, 255, 255, 22);
                border-radius: 7px;
                color: rgba(241, 243, 248, 190);
                font-size: 13px;
                alternate-background-color: rgba(255, 255, 255, 10);
            }}
            QTableWidget#vaultTable::item {{
                border: none;
                padding: 10px;
            }}
            QTableWidget#vaultTable::item:selected {{
                background: rgba(255, 63, 145, 58);
                color: white;
            }}
            QComboBox#comboField,
            QSpinBox#comboField {{
                min-height: 42px;
                border-radius: 7px;
                padding: 0 12px;
                background: rgba(13, 15, 20, 226);
                border: 1px solid rgba(255, 255, 255, 34);
                color: {TEXT};
                font-size: 13px;
            }}
            QComboBox#comboField:hover,
            QComboBox#comboField:focus,
            QSpinBox#comboField:hover,
            QSpinBox#comboField:focus {{
                border-color: rgba(255, 63, 145, 145);
            }}
            QSpinBox#comboField::up-button,
            QSpinBox#comboField::down-button {{
                background: rgba(20, 22, 29, 170);
                border: none;
                width: 18px;
            }}
            QCheckBox#checkField {{
                color: rgba(241, 243, 248, 190);
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox#checkField::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                background: rgba(13, 15, 20, 226);
                border: 1px solid rgba(255, 255, 255, 48);
            }}
            QCheckBox#checkField::indicator:checked {{
                background: rgba(255, 63, 145, 180);
                border-color: rgba(255, 145, 190, 210);
            }}
            QComboBox#comboField::drop-down {{
                border: none;
                width: 28px;
            }}
            QComboBox#comboField QAbstractItemView {{
                background: rgba(13, 15, 20, 245);
                border: 1px solid rgba(255, 63, 145, 110);
                color: {TEXT};
                selection-background-color: rgba(255, 63, 145, 85);
            }}
            QTextEdit#notesField {{
                border-radius: 7px;
                padding: 10px 12px;
                background: rgba(13, 15, 20, 226);
                border: 1px solid rgba(255, 255, 255, 34);
                color: {TEXT};
                font-size: 13px;
                selection-background-color: rgba(255, 63, 145, 110);
            }}
            QTextEdit#notesField:focus {{
                border-color: rgba(255, 63, 145, 150);
            }}
            QLabel#detailTitle {{
                color: {TEXT};
                font-size: 22px;
                font-weight: 820;
            }}
            QLabel#detailSubtle {{
                color: rgba(255, 106, 169, 178);
                font-size: 12px;
                font-weight: 700;
            }}
            QLabel#detailLine {{
                color: rgba(218, 221, 230, 185);
                background: rgba(255, 255, 255, 12);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 5px;
                padding: 8px 10px;
                font-size: 12px;
            }}
            QLabel#detailNote {{
                color: rgba(218, 221, 230, 170);
                background: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 18);
                border-left: 2px solid rgba(255, 63, 145, 126);
                border-radius: 5px;
                padding: 10px;
                font-size: 12px;
            }}
            QHeaderView::section {{
                background: rgba(17, 19, 25, 230);
                color: rgba(218, 221, 230, 170);
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 26);
                padding: 8px 10px;
                font-size: 11px;
                font-weight: 800;
            }}
            QPushButton#actionButton {{
                min-height: 64px;
                background: rgba(13, 15, 20, 205);
                border: 1px solid rgba(255, 255, 255, 26);
                border-radius: 8px;
                color: rgba(241, 243, 248, 205);
                font-size: 13px;
                font-weight: 750;
                text-align: left;
                padding-left: 14px;
            }}
            QPushButton#actionButton:hover {{
                background: rgba(28, 30, 38, 190);
                border-color: rgba(255, 63, 145, 128);
                color: white;
            }}
            QLabel#securityLabel {{
                color: rgba(218, 221, 230, 178);
                font-size: 12px;
            }}
            QLabel#securityValue {{
                color: {MAGENTA_SOFT};
                font-size: 12px;
                font-weight: 720;
            }}
            QLabel#activityLine {{
                color: rgba(218, 221, 230, 172);
                background: rgba(255, 255, 255, 12);
                border: 1px solid rgba(255, 255, 255, 20);
                border-left: 2px solid rgba(255, 63, 145, 130);
                border-radius: 5px;
                padding: 8px 10px;
                font-size: 12px;
            }}
            QLabel#dashboardStatus {{
                min-height: 34px;
                color: rgba(241, 243, 248, 185);
                background: rgba(8, 9, 13, 190);
                border: 1px solid rgba(255, 255, 255, 22);
                border-left: 2px solid rgba(255, 63, 145, 150);
                border-radius: 7px;
                padding: 0 12px;
                font-size: 12px;
            }}
            QLabel#title {{
                color: {TEXT};
                font-size: 28px;
                font-weight: 750;
            }}
            QLabel#subtitle {{
                color: rgba(255, 106, 169, 185);
                font-size: 13px;
            }}
            ModeButton,
            QPushButton {{
                outline: none;
            }}
            QPushButton:checked {{
                background: rgba(255, 63, 145, 42);
                border-color: rgba(255, 63, 145, 172);
                color: white;
            }}
            QPushButton {{
                border-radius: 6px;
            }}
            QPushButton#modeButton {{
                background: rgba(20, 22, 29, 190);
                border: 1px solid rgba(255, 255, 255, 30);
                color: rgba(241, 243, 248, 185);
            }}
            QPushButton#modeButton:hover {{
                border-color: rgba(255, 63, 145, 120);
                color: white;
            }}
            QPushButton#modeButton:checked {{
                background: rgba(255, 63, 145, 44);
                border-color: rgba(255, 63, 145, 170);
                color: white;
            }}
            QLineEdit#field {{
                min-height: 48px;
                border-radius: 7px;
                padding: 0 15px;
                background: rgba(13, 15, 20, 226);
                border: 1px solid rgba(255, 255, 255, 34);
                color: {TEXT};
                font-size: 15px;
                selection-background-color: rgba(255, 63, 145, 120);
            }}
            QLineEdit#field:focus {{
                border: 1px solid rgba(255, 63, 145, 172);
                background: rgba(17, 19, 25, 238);
            }}
            QLineEdit#field::placeholder {{
                color: rgba(157, 161, 173, 150);
            }}
            QLineEdit#formField {{
                min-height: 38px;
                border-radius: 7px;
                padding: 0 14px;
                background: rgba(13, 15, 20, 226);
                border: 1px solid rgba(255, 255, 255, 34);
                color: {TEXT};
                font-size: 14px;
                selection-background-color: rgba(255, 63, 145, 120);
            }}
            QLineEdit#formField:focus {{
                border: 1px solid rgba(255, 63, 145, 172);
                background: rgba(17, 19, 25, 238);
            }}
            QLineEdit#formField::placeholder {{
                color: rgba(157, 161, 173, 150);
            }}
            QPushButton#ghostButton {{
                min-height: 30px;
                padding: 0 14px;
                background: rgba(18, 20, 26, 170);
                border: 1px solid rgba(255, 255, 255, 32);
                color: rgba(241, 243, 248, 178);
            }}
            QPushButton#ghostButton:hover {{
                border-color: rgba(255, 63, 145, 135);
                color: white;
            }}
            QLabel#hint {{
                color: rgba(157, 161, 173, 180);
                font-size: 12px;
            }}
            QPushButton#primaryButton {{
                min-height: 50px;
                background: rgba(255, 63, 145, 210);
                border: 1px solid rgba(255, 145, 190, 210);
                color: white;
                font-size: 15px;
                font-weight: 800;
            }}
            QPushButton#primaryButton:hover {{
                background: rgba(255, 83, 157, 230);
            }}
            QLabel#statusLabel {{
                min-height: 28px;
                color: rgba(241, 243, 248, 180);
                background: rgba(255, 255, 255, 14);
                border: 1px solid rgba(255, 255, 255, 22);
                border-left: 2px solid rgba(255, 63, 145, 160);
                border-radius: 5px;
                padding: 8px 10px;
                font-size: 12px;
            }}
            QFrame#divider {{
                background: rgba(255, 255, 255, 24);
                border: none;
            }}
            QFrame#metric {{
                background: rgba(17, 19, 25, 165);
                border: 1px solid rgba(255, 255, 255, 24);
                border-radius: 6px;
            }}
            QLabel#metricLabel {{
                color: rgba(157, 161, 173, 155);
                font-size: 9px;
                font-weight: 700;
            }}
            QLabel#metricValue {{
                color: {MAGENTA_SOFT};
                font-size: 12px;
                font-weight: 800;
            }}
        """


def configure_app(app: QApplication) -> None:
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Rat Mode")
    app.setWindowIcon(QIcon(str(asset_path("coding-rat-reference.png"))))
    app.setFont(QFont("Inter", 10))


def main() -> int:
    app = QApplication(sys.argv)
    configure_app(app)
    window = PortalWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
