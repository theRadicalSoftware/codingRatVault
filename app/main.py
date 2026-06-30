from __future__ import annotations

import secrets
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QComboBox,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "Coding Rat Vault"
APP_VERSION = "0.1.0"
DEMO_ACCESS_ID = "rat@vault.local"
DEMO_PASSPHRASE = "ratmode-demo-2026"
MAGENTA = "#ff3f91"
MAGENTA_SOFT = "#ff6aa9"
INK = "#050608"
CHARCOAL = "#101217"
GRAPHITE = "#1b1e24"
MUTED = "#9da1ad"
TEXT = "#f1f3f8"


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

    @property
    def masked_password(self) -> str:
        return "*" * max(10, min(len(self.password), 18))

    def searchable_text(self) -> str:
        return " ".join([
            self.service,
            self.account,
            self.username,
            self.url,
            self.folder,
            self.entry_type,
            self.notes,
            self.health,
        ]).lower()


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

        node_w = max(118, min(142, self.width() - 24))
        node_h = 44
        center_x = max(14, (self.width() - node_w) // 2)
        root = self.node_buttons.get("All")
        if root:
            root.move(center_x, 12)
            root.resize(node_w, node_h)

        children = [name for name, _count in self.folders if name != "All"]
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


class DashboardWidget(QWidget):
    def __init__(self, on_lock):
        super().__init__()
        self.on_lock = on_lock
        self.credentials = self.seed_credentials()
        self.nav_buttons: dict[str, NavButton] = {}
        self.folder_chip_buttons: dict[str, QPushButton] = {}
        self.active_folder = "All"
        self.visible_credentials: list[CredentialEntry] = []
        self.build_ui()
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
        self.add_entry_view = self.build_add_entry_view()
        self.content_stack.addWidget(self.overview_view)
        self.content_stack.addWidget(self.vault_view)
        self.content_stack.addWidget(self.add_entry_view)
        root.addWidget(self.content_host, 1)

    def seed_credentials(self) -> list[CredentialEntry]:
        return [
            CredentialEntry(
                service="GitHub Workspace",
                account="theRadicalSoftware",
                username="rat@vault.local",
                password="demo-github-pass-2026",
                url="https://github.com/theRadicalSoftware",
                folder="Development",
                entry_type="Login",
                notes="Public demo credential for the UI prototype.",
                health="Strong",
                updated="Today",
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
                updated="Today",
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
                updated="Yesterday",
            ),
        ]

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

        for index, label in enumerate(["Overview", "Vault", "Generator", "Security", "Settings"]):
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
        session_state = QLabel("Sealed in memory")
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
        self.storage_stat = StatCard("Storage", "Local", "Session memory only")
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
            ("Import", "Bring records in"),
            ("Audit", "Run checks"),
        ]
        for index, (label, detail) in enumerate(actions):
            button = QPushButton(f"{label}\n{detail}")
            button.setObjectName("actionButton")
            button.setCursor(Qt.PointingHandCursor)
            if label == "New Login":
                button.clicked.connect(self.show_add_entry)
            elif label == "Audit":
                button.clicked.connect(lambda: self.set_session_message("Audit will inspect stored entries once persistence is connected."))
            else:
                button.clicked.connect(lambda _checked=False, text=label: self.set_session_message(f"{text} flow comes next."))
            grid.addWidget(button, index // 2, index % 2)
        panel.layout.addLayout(grid)
        return panel

    def build_security_panel(self) -> QWidget:
        panel = SectionPanel("Security Posture")
        rows = [
            ("Master key", "Accepted for this session"),
            ("Clipboard", "Auto-clear planned"),
            ("Breach checks", "Waiting for vault data"),
            ("Travel mode", "Requires real backup first"),
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
        subtitle = QLabel("Browse, filter, inspect, and copy credentials from the current unlocked session.")
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

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        for label in ["All", "Development", "Infrastructure", "Creative", "Personal", "Finance"]:
            button = QPushButton(label)
            button.setObjectName("chipButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, folder=label: self.set_folder_filter(folder))
            self.folder_chip_buttons[label] = button
            if label == "All":
                button.setChecked(True)
            filter_row.addWidget(button)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.vault_table = self.create_credentials_table()
        self.vault_table.setMinimumHeight(430)
        self.vault_table.itemSelectionChanged.connect(self.on_vault_selection_changed)
        body.addWidget(self.vault_table, 7)

        map_panel = SectionPanel("Folders", "Jump by workspace lane.")
        map_panel.setMinimumWidth(172)
        self.folder_map = FolderMapWidget()
        self.folder_map.folder_selected.connect(self.set_folder_filter)
        map_panel.layout.addWidget(self.folder_map, 1)
        body.addWidget(map_panel, 2)

        details = SectionPanel("Credential Detail", "Selected account surface.")
        details.setMinimumWidth(292)
        self.detail_service = QLabel("No credential selected")
        self.detail_service.setObjectName("detailTitle")
        self.detail_service.setWordWrap(True)
        self.detail_account = QLabel("Choose a row in the table.")
        self.detail_account.setObjectName("detailSubtle")
        self.detail_url = QLabel("")
        self.detail_url.setObjectName("detailLine")
        self.detail_username = QLabel("")
        self.detail_username.setObjectName("detailLine")
        self.detail_password = QLabel("")
        self.detail_password.setObjectName("detailLine")
        self.detail_notes = QLabel("")
        self.detail_notes.setObjectName("detailNote")
        for detail_label in [
            self.detail_account,
            self.detail_url,
            self.detail_username,
            self.detail_password,
            self.detail_notes,
        ]:
            detail_label.setWordWrap(True)

        details.layout.addWidget(self.detail_service)
        details.layout.addWidget(self.detail_account)
        details.layout.addWidget(self.detail_url)
        details.layout.addWidget(self.detail_username)
        details.layout.addWidget(self.detail_password)
        details.layout.addWidget(self.detail_notes)

        copy_row = QHBoxLayout()
        copy_user = QPushButton("Copy User")
        copy_user.setObjectName("secondaryButton")
        copy_user.setCursor(Qt.PointingHandCursor)
        copy_user.clicked.connect(lambda: self.copy_selected_value("username"))
        copy_pass = QPushButton("Copy Pass")
        copy_pass.setObjectName("secondaryButton")
        copy_pass.setCursor(Qt.PointingHandCursor)
        copy_pass.clicked.connect(lambda: self.copy_selected_value("password"))
        copy_row.addWidget(copy_user)
        copy_row.addWidget(copy_pass)
        details.layout.addLayout(copy_row)
        details.layout.addStretch(1)
        body.addWidget(details, 4)

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
        eyebrow = QLabel("NEW CREDENTIAL")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Add Entry")
        title.setObjectName("dashboardTitle")
        subtitle = QLabel("Capture the account details now; encryption and persistence will attach in the next backend slice.")
        subtitle.setObjectName("dashboardSubtitle")
        subtitle.setWordWrap(True)
        title_stack.addWidget(eyebrow)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack, 1)

        cancel_button = QPushButton("Back to Vault")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.clicked.connect(self.show_vault)
        header.addWidget(cancel_button)
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
        self.folder_combo.addItems(["Development", "Infrastructure", "Creative", "Personal", "Finance"])
        self.type_combo = QComboBox()
        self.type_combo.setObjectName("comboField")
        self.type_combo.addItems(["Login", "API Key", "Server", "Database", "Secure Note"])
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
        form.addRow("Notes", self.notes_field)
        form_panel.layout.addLayout(form)

        action_row = QHBoxLayout()
        generate_button = QPushButton("Generate")
        generate_button.setObjectName("secondaryButton")
        generate_button.setCursor(Qt.PointingHandCursor)
        generate_button.clicked.connect(self.generate_entry_password)
        save_button = QPushButton("Save Entry")
        save_button.setObjectName("primarySmallButton")
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.clicked.connect(self.save_entry)
        action_row.addWidget(generate_button)
        action_row.addStretch(1)
        action_row.addWidget(save_button)
        form_panel.layout.addLayout(action_row)
        body.addWidget(form_panel, 3)

        guidance = SectionPanel("Entry Guidance")
        for text in [
            "Use names that are easy to scan later.",
            "Keep recovery hints in notes, not full recovery codes.",
            "Folder and type choices will become real filters in the persistent vault.",
            "This prototype stores entries in memory for the current session only.",
        ]:
            label = QLabel(text)
            label.setObjectName("activityLine")
            label.setWordWrap(True)
            guidance.layout.addWidget(label)
        guidance.layout.addStretch(1)
        body.addWidget(guidance, 2)
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
        else:
            self.activate_nav(name)
            self.set_session_message(f"{name} workspace is planned for the next product slice.")

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

    def show_add_entry(self) -> None:
        self.activate_nav("Vault")
        self.content_stack.setCurrentWidget(self.add_entry_view)
        self.service_field.setFocus()
        self.set_session_message("Add a new credential.")

    def search_from_overview(self) -> None:
        query = self.global_search_input.text().strip()
        self.vault_search_input.setText(query)
        self.show_vault()

    def folder_counts(self) -> list[tuple[str, int]]:
        folder_order = ["Development", "Infrastructure", "Creative", "Personal", "Finance"]
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

    def refresh_all(self) -> None:
        folders = sorted({entry.folder for entry in self.credentials})
        weak_count = len([entry for entry in self.credentials if entry.health == "Weak"])
        self.entries_stat.update_values(str(len(self.credentials)), "Stored in this demo session")
        self.folders_stat.update_values(str(len(folders)), "Active folder lanes")
        self.security_stat.update_values("Ready" if weak_count == 0 else "Review", f"{weak_count} weak entries")
        self.storage_stat.update_values("Memory", "Persistence comes next")
        self.populate_table(self.overview_table, self.credentials[:5], empty_text="No entries yet. Add your first credential.")
        if hasattr(self, "folder_map"):
            self.folder_map.set_folders(self.folder_counts(), self.active_folder)
        self.sync_folder_controls()
        self.refresh_vault_tables()

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
        selected = self.vault_table.selectionModel().selectedRows() if hasattr(self, "vault_table") else []
        if not selected:
            return None
        row = selected[0].row()
        if 0 <= row < len(self.visible_credentials):
            return self.visible_credentials[row]
        return None

    def update_detail(self, entry: CredentialEntry | None) -> None:
        if entry is None:
            self.detail_service.setText("No credential selected")
            self.detail_account.setText("Choose a row in the table.")
            self.detail_url.setText("")
            self.detail_username.setText("")
            self.detail_password.setText("")
            self.detail_notes.setText("")
            return
        self.detail_service.setText(entry.service)
        self.detail_account.setText(f"{entry.account} - {entry.folder} / {entry.entry_type}")
        self.detail_url.setText(f"URL: {entry.url or 'Not set'}")
        self.detail_username.setText(f"User: {entry.username or 'Not set'}")
        self.detail_password.setText(f"Password: {entry.masked_password}")
        self.detail_notes.setText(entry.notes or "No notes stored for this entry.")

    def copy_selected_value(self, field: str) -> None:
        entry = self.selected_entry()
        if entry is None:
            self.set_session_message("Select a credential first.")
            return
        value = entry.username if field == "username" else entry.password
        QApplication.clipboard().setText(value)
        label = "username" if field == "username" else "password"
        self.set_session_message(f"Copied {label} for {entry.service}. Clipboard auto-clear is planned.")
        QTimer.singleShot(30000, lambda copied=value: self.clear_clipboard_if_unchanged(copied))

    def clear_clipboard_if_unchanged(self, copied: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard.text() == copied:
            clipboard.clear()
            self.set_session_message("Clipboard cleared.")

    def generate_entry_password(self) -> None:
        generated = f"rat-{secrets.token_urlsafe(16)}"
        self.entry_password_field.setText(generated)
        self.set_session_message("Generated a strong session password.")

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
        )
        self.credentials.insert(0, entry)
        self.clear_entry_form()
        self.active_folder = entry.folder
        if hasattr(self, "vault_search_input"):
            self.vault_search_input.clear()
        self.refresh_all()
        self.show_vault()
        self.set_session_message(f"Added {entry.service} to the session vault.")

    def clear_entry_form(self) -> None:
        for field in [self.service_field, self.account_field, self.username_field, self.entry_password_field, self.url_field]:
            field.clear()
        self.folder_combo.setCurrentIndex(0)
        self.type_combo.setCurrentIndex(0)
        self.notes_field.clear()

    def calculate_health(self, password: str) -> str:
        if len(password) >= 16:
            return "Strong"
        if len(password) >= 10:
            return "Good"
        return "Weak"

    def set_session_message(self, message: str) -> None:
        if hasattr(self, "session_status"):
            self.session_status.setText(message)


class PortalWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.drag_position = QPoint()
        self.mode = "unlock"
        self.transient_secret = bytearray()
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
        self.dashboard_view = DashboardWidget(self.lock_to_portal)
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
        self.mode_hint = QLabel("Vault core pending")
        self.mode_hint.setObjectName("hint")
        aux_row.addWidget(self.mode_hint)
        panel_layout.addLayout(aux_row)

        self.submit_button = QPushButton("Unlock Vault")
        self.submit_button.setObjectName("primaryButton")
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.clicked.connect(self.submit)
        panel_layout.addWidget(self.submit_button)

        self.status_label = QLabel("Use the demo account to test login")
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
        self.mode_hint.setText("New local vault" if is_create else "Demo account enabled")
        self.status_label.setText("Choose an access ID and master key" if is_create else "Use the demo account to test login")
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
        self.status_label.setText("Demo account loaded")
        self.passphrase_input.setFocus()

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
            if len(secret) < 10:
                self.status_label.setText("Use at least 10 characters")
                self.clear_transient_secret()
                self.shake_panel()
                return
            if secret != confirm:
                self.status_label.setText("Confirmation does not match")
                self.clear_transient_secret()
                self.shake_panel()
                return
            message = f"New vault session initialized for {access_id}."
        else:
            if access_id.lower() != DEMO_ACCESS_ID or secret != DEMO_PASSPHRASE:
                self.status_label.setText("Demo account mismatch")
                self.clear_transient_secret()
                self.shake_panel()
                return
            message = f"Demo vault unlocked for {access_id}."

        self.clear_transient_secret()
        self.access_id_input.clear()
        self.passphrase_input.clear()
        self.confirm_input.clear()
        self.show_dashboard(message)

    def show_dashboard(self, message: str) -> None:
        self.top_status.setText("VAULT DASHBOARD")
        self.view_stack.setCurrentWidget(self.dashboard_view)
        self.dashboard_view.set_session_message(message)

    def lock_to_portal(self) -> None:
        self.clear_transient_secret()
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
            QPushButton#secondaryButton {{
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
            QComboBox#comboField {{
                min-height: 42px;
                border-radius: 7px;
                padding: 0 12px;
                background: rgba(13, 15, 20, 226);
                border: 1px solid rgba(255, 255, 255, 34);
                color: {TEXT};
                font-size: 13px;
            }}
            QComboBox#comboField:hover,
            QComboBox#comboField:focus {{
                border-color: rgba(255, 63, 145, 145);
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
