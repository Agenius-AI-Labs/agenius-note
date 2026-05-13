"""ALStatusBar — colored badge above the main content while Active Listening runs.

State drives both background colour (via QSS `[state="..."]`) and label text.
States: idle | loading | listening | wake-detected | recording | transcribing.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from .helpers import restyle


_STATE_TEXT = {
    "loading":       "⏳  Loading wake-word model…",
    "listening":     "👂  Listening for wake word…",
    "wake-detected": "🎯  Wake word detected, speak now",
    "recording":     "🔴  Recording…  (silence will auto-stop)",
    "transcribing":  "⚙  Transcribing…",
    "parsing":       "✨  Parsing transcript…",
}


class ALStatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("alStatusBar")
        self.setProperty("state", "idle")
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(8)

        self._label = QLabel("", self)
        self._label.setObjectName("alStatusText")
        self._label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        layout.addWidget(self._label)
        layout.addStretch(1)

    def set_state(self, state: str, model_name: str = "") -> None:
        if state == "idle":
            self.setVisible(False)
            self.setProperty("state", "idle")
            self._label.setText("")
            restyle(self)
            return

        text = _STATE_TEXT.get(state, "")
        if state == "listening" and model_name:
            text = f"👂  Listening for ‘{model_name}’ — say it to dictate"
        elif state == "loading" and model_name:
            text = f"⏳  Loading wake-word model: {model_name}…"

        self.setProperty("state", state)
        self._label.setText(text)
        self.setVisible(True)
        restyle(self)
