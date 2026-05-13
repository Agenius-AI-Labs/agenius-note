"""Card widget — task or note row in the list panels.

Visual:
    ┌──┐ Title                     [pill]
    │  │ #5  ·  high  ·  open  ·  voice
    │  │ Body preview text wraps to two lines…
    │  │ #tag1  #tag2  #tag3
    │  │ [✓ Done] [🔊 Read] [Delete]
    └──┘
The 3-px left accent bar colour is driven by `kind` property
(task / note / task-done / note-done).
"""

from __future__ import annotations

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .helpers import restyle
from .widgets.flow_layout import FlowLayout


def _coerce_tags(raw) -> list[str]:
    if isinstance(raw, list):
        return [str(t) for t in raw if str(t).strip()]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(t) for t in parsed if str(t).strip()]
        except Exception:
            return [t.strip() for t in raw.split(",") if t.strip()]
    return []


class Card(QFrame):
    """Generic card row.

    Signals:
        clicked(int)         — click anywhere on the card body (edit)
        toggle_done(int)     — task-only "Complete / Reopen" pressed
        delete_clicked(int)  — Delete pressed
    """

    clicked        = Signal(int)
    toggle_done    = Signal(int)
    delete_clicked = Signal(int)

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self._item = dict(item)
        self.setProperty("class", "card")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        is_task = item.get("item_type") == "task"
        is_done = item.get("status") == "done"
        kind = (
            ("task-done" if is_done else "task") if is_task
            else ("note-done" if is_done else "note")
        )
        self.setProperty("done", bool(is_done))

        self._build(is_task, is_done, kind)

    # ── Build ─────────────────────────────────────────────────

    def _build(self, is_task: bool, is_done: bool, kind: str) -> None:
        item = self._item

        # Outer: HBox = [accent | content]
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        accent = QFrame(self)
        accent.setObjectName("cardAccent")
        accent.setProperty("kind", kind)
        accent.setFixedWidth(3)
        outer.addWidget(accent)

        body_w = QWidget(self)
        body = QVBoxLayout(body_w)
        body.setContentsMargins(16, 12, 16, 12)
        body.setSpacing(6)

        # Header row: title + priority pill
        header = QHBoxLayout()
        header.setSpacing(10)

        title_text = item.get("title") or "(untitled)"
        title_lbl = QLabel(title_text, body_w)
        title_lbl.setObjectName("cardTitle")
        title_lbl.setWordWrap(True)
        header.addWidget(title_lbl, 1)

        if is_task:
            pill = QLabel((item.get("priority") or "normal").upper(), body_w)
            pill.setProperty("class", "pill")
            pill.setProperty("level", item.get("priority") or "normal")
            pill.setAlignment(Qt.AlignCenter)
            header.addWidget(pill, 0, Qt.AlignTop)

        body.addLayout(header)

        # Meta line
        meta = " · ".join(filter(None, [
            f"#{item.get('id')}",
            item.get("priority") or None,
            item.get("status") or None,
            item.get("source") or None,
        ]))
        meta_lbl = QLabel(meta, body_w)
        meta_lbl.setObjectName("cardMeta")
        body.addWidget(meta_lbl)

        # Body preview (truncated)
        raw_body = (item.get("body") or "").strip()
        if raw_body:
            preview = raw_body if len(raw_body) <= 240 else raw_body[:240].rstrip() + "…"
            body_lbl = QLabel(preview, body_w)
            body_lbl.setObjectName("cardBody")
            body_lbl.setWordWrap(True)
            body.addWidget(body_lbl)

        # Tags
        tags = _coerce_tags(item.get("tags"))[:6]
        if tags:
            tag_holder = QWidget(body_w)
            flow = FlowLayout(tag_holder, margin=0, h_spacing=6, v_spacing=6)
            for t in tags:
                chip = QLabel(f"#{t}", tag_holder)
                chip.setProperty("class", "tagChip")
                flow.addWidget(chip)
            body.addWidget(tag_holder)

        # Actions
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.setContentsMargins(0, 6, 0, 0)

        if is_task:
            self._done_btn = QPushButton("↺  Reopen" if is_done else "✓  Complete", body_w)
            self._done_btn.setObjectName("ghost" if is_done else "success")
            self._done_btn.setCursor(Qt.PointingHandCursor)
            self._done_btn.clicked.connect(self._on_done_clicked)
            actions.addWidget(self._done_btn)
        else:
            self._done_btn = None

        actions.addStretch(1)

        del_btn = QPushButton("Delete", body_w)
        del_btn.setObjectName("danger")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(self._on_delete_clicked)
        actions.addWidget(del_btn)

        body.addLayout(actions)

        outer.addWidget(body_w, 1)

    # ── Public API ────────────────────────────────────────────

    @property
    def item_id(self) -> int:
        return int(self._item.get("id", 0))

    # ── Event handling ────────────────────────────────────────

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        # Forward only background clicks (not propagated from buttons).
        if ev.button() == Qt.LeftButton:
            self.clicked.emit(self.item_id)
        super().mousePressEvent(ev)

    # ── Slots ─────────────────────────────────────────────────

    def _on_done_clicked(self) -> None:
        self.toggle_done.emit(self.item_id)

    def _on_delete_clicked(self) -> None:
        self.delete_clicked.emit(self.item_id)


class TaskCard(Card):
    """Task variant — included for explicit typing/instantiation."""


class NoteCard(Card):
    """Note variant — included for explicit typing/instantiation."""
