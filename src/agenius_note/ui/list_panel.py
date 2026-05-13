"""ListPanel — scrollable list of Cards for one item_type (task or note).

Header: title (Tasks/Notes), count, status filter, search box.
Scroll area: vertical QVBoxLayout of Card widgets.

Cards forward their action signals up through `item_clicked` (edit),
`toggle_done`, and `delete_clicked` so MainWindow can drive global state.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.db import db_delete, db_list, db_update
from .card import Card
from .signals import AppSignals


class ListPanel(QWidget):
    item_clicked = Signal(int)  # forwarded to MainWindow → CapturePanel.load_item_for_edit

    HEADERS = {"task": "Tasks", "note": "Notes"}

    def __init__(self, item_type: str, signals: AppSignals, parent=None):
        super().__init__(parent)
        if item_type not in ("task", "note"):
            raise ValueError(f"item_type must be task|note, got {item_type!r}")
        self._item_type = item_type
        self._signals = signals
        self._cards: dict[int, Card] = {}

        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(180)
        self._search_debounce.timeout.connect(self._refresh)

        self._build()
        self._wire()
        self._refresh()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(16)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        h1 = QLabel(self.HEADERS[self._item_type], self)
        h1.setProperty("class", "h1")
        header.addWidget(h1)

        self._count = QLabel("", self)
        self._count.setProperty("class", "dim mono")
        header.addWidget(self._count)

        header.addStretch(1)

        self._status_combo = QComboBox(self)
        self._status_combo.addItems(["all", "open", "done"])
        self._status_combo.setCurrentText("open" if self._item_type == "task" else "all")
        header.addWidget(self._status_combo)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search…")
        self._search.setClearButtonEnabled(True)
        self._search.setFixedWidth(220)
        header.addWidget(self._search)

        outer.addLayout(header)

        # Scrollable card list
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QScrollArea.NoFrame)

        self._list_host = QWidget(self._scroll)
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(10)
        self._list_layout.addStretch(1)
        self._scroll.setWidget(self._list_host)

        outer.addWidget(self._scroll, 1)

    def _wire(self) -> None:
        self._status_combo.currentTextChanged.connect(lambda _: self._refresh())
        self._search.textChanged.connect(lambda _: self._search_debounce.start())
        self._signals.items_changed.connect(self._on_items_changed)

    # ── Refresh / render ──────────────────────────────────────

    def _refresh(self) -> None:
        rows = db_list(
            item_type=self._item_type,
            status=self._status_combo.currentText() or "all",
            q=self._search.text(),
        )
        self._render(rows)

    def _render(self, rows: list[dict]) -> None:
        # Clear existing cards
        for card in list(self._cards.values()):
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

        # Insert cards above the trailing stretch (which is the last item).
        insert_at = max(self._list_layout.count() - 1, 0)
        for row in rows:
            card = Card(row, self._list_host)
            card.clicked.connect(self.item_clicked.emit)
            card.toggle_done.connect(self._on_toggle_done)
            card.delete_clicked.connect(self._on_delete_clicked)
            self._list_layout.insertWidget(insert_at, card)
            self._cards[int(row["id"])] = card
            insert_at += 1

        self._count.setText(f"{len(rows)} {self._item_type}s")

    # ── Action slots ──────────────────────────────────────────

    @Slot(int)
    def _on_toggle_done(self, item_id: int) -> None:
        card = self._cards.get(item_id)
        if card is None:
            return
        current = card._item.get("status") or "open"
        new_status = "open" if current == "done" else "done"
        db_update(item_id, {"status": new_status})
        self._signals.items_changed.emit(self._item_type)

    @Slot(int)
    def _on_delete_clicked(self, item_id: int) -> None:
        db_delete(item_id)
        self._signals.items_changed.emit(self._item_type)

    @Slot(str)
    def _on_items_changed(self, scope: str) -> None:
        if scope in ("all", self._item_type):
            self._refresh()
