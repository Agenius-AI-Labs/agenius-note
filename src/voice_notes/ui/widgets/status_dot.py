"""Tiny pulsing status dot for the sidebar footer."""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect

from ..helpers import restyle


class StatusDot(QFrame):
    """8x8 round dot whose colour comes from QSS `[state="..."]`.

    States: idle | online | offline | checking | active.
    `checking` and `active` pulse opacity gently for liveness.
    """

    def __init__(self, parent=None, state: str = "idle"):
        super().__init__(parent)
        self.setObjectName("statusDot")
        self.setFixedSize(8, 8)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)
        self._anim: QPropertyAnimation | None = None
        self.set_state(state)

    def set_state(self, state: str) -> None:
        self.setProperty("state", state)
        restyle(self)
        self._refresh_pulse(state)

    def _refresh_pulse(self, state: str) -> None:
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        if state in ("checking", "active"):
            anim = QPropertyAnimation(self._effect, b"opacity", self)
            anim.setDuration(1500)
            anim.setStartValue(1.0)
            anim.setKeyValueAt(0.5, 0.4)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.InOutSine)
            anim.setLoopCount(-1)
            anim.start()
            self._anim = anim
        else:
            self._effect.setOpacity(1.0)
