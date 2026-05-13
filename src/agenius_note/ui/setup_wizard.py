"""First-run setup wizard.

Six pages: Welcome → Whisper model → Wake word → AI backend → Downloads → Done.
Saves all picks via db_set_setting and flips first_run_complete=1 on finish.

The Downloads page kicks off the model fetches when entered so the user
isn't waiting at the mic on first click.
"""

from __future__ import annotations

from pathlib import Path

import threading

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from ..core.anthropic_parse import probe_anthropic
from ..core.db import db_get_setting, db_set_setting
from ..core.downloads import DownloadManager
from ..core.keystore import get_secret, set_secret
from ..core.ollama_parse import probe_endpoint
from ..core.openai_parse import probe_openai
from ..core.wakeword import HAS_OWW, get_oww_models


# Per-backend metadata used by the consistent backend-row builder.
_BACKEND_LINKS = {
    "openai": ('Get an API key at '
               '<a href="https://platform.openai.com/api-keys" '
               'style="color: #38bdf8; text-decoration: none;">'
               'platform.openai.com/api-keys</a>.'),
    "anthropic": ('Get an API key at '
                  '<a href="https://console.anthropic.com/settings/keys" '
                  'style="color: #38bdf8; text-decoration: none;">'
                  'console.anthropic.com/settings/keys</a>.'),
    "ollama": ('Don\'t have Ollama? '
               '<a href="https://ollama.com/download" '
               'style="color: #38bdf8; text-decoration: none;">'
               'Download for your OS</a>, then run <code>ollama pull llama3.2</code>.'),
}

_ASSETS = Path(__file__).resolve().parents[1] / "assets"


WHISPER_OPTIONS = [
    # (id, label, size, blurb)
    ("tiny.en",   "Tiny (English)",   "~39 MB",  "Fastest, lowest accuracy. Good on slow CPUs."),
    ("base.en",   "Base (English)",   "~74 MB",  "Recommended. Solid quality, fast on most machines."),
    ("small.en",  "Small (English)",  "~244 MB", "Higher accuracy. Slower on CPU; great with a GPU."),
    ("medium.en", "Medium (English)", "~769 MB", "Best accuracy. GPU strongly recommended."),
]


def _h1(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 20px; font-weight: 700;")
    return lbl


def _muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet("color: rgba(180, 200, 230, 0.7); font-size: 12px;")
    return lbl


# ── Pages ─────────────────────────────────────────────────────


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle(" ")
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(_h1("Welcome to AgeniusNote"))
        layout.addWidget(_muted(
            "Let's get you set up. This takes about a minute and downloads "
            "the speech-to-text model so your first mic click is instant."
        ))
        layout.addStretch(1)
        layout.addWidget(_muted(
            "You can change any of these choices later in Settings."
        ))


class WhisperPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle(" ")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(_h1("Pick a transcription model"))
        layout.addWidget(_muted(
            "Whisper transcribes your speech. Bigger models are more accurate "
            "but slower on CPU."
        ))

        self._group = QButtonGroup(self)
        current = db_get_setting("whisper_model", "base.en") or "base.en"

        for model_id, label, size, blurb in WHISPER_OPTIONS:
            row = QWidget(self)
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(0, 4, 0, 4)
            row_l.setSpacing(10)
            rb = QRadioButton(row)
            rb.setText(f"{label}  ·  {size}")
            rb.setProperty("model_id", model_id)
            if model_id == current:
                rb.setChecked(True)
            self._group.addButton(rb)
            row_l.addWidget(rb)
            row_l.addWidget(_muted(blurb), 1)
            layout.addWidget(row)

        if not any(b.isChecked() for b in self._group.buttons()):
            self._group.buttons()[1].setChecked(True)  # base.en

        layout.addStretch(1)

    def chosen_model(self) -> str:
        for b in self._group.buttons():
            if b.isChecked():
                return b.property("model_id") or "base.en"
        return "base.en"

    def validatePage(self) -> bool:
        db_set_setting("whisper_model", self.chosen_model())
        return True


class WakeWordPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle(" ")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(_h1("Wake word (optional)"))
        layout.addWidget(_muted(
            "Active Listening watches for a wake phrase, then auto-records. "
            "You can always push-to-talk instead. Custom models can be trained "
            "later via the openWakeWord Colab notebook (linked in Settings)."
        ))

        self._enable = QCheckBox("Enable wake-word activation", self)
        current_path = (db_get_setting("al_model_path", "") or "").strip()
        already_on = bool(current_path) or db_get_setting("al_enabled", "0") == "1"
        self._enable.setChecked(already_on)
        layout.addWidget(self._enable)

        if not HAS_OWW:
            layout.addWidget(_muted(
                "openwakeword is not installed in this environment. "
                "This step will be skipped."
            ))
            self._enable.setChecked(False)
            self._enable.setEnabled(False)

        self._combo = QComboBox(self)
        models = get_oww_models()
        self._combo.addItems(models)
        current = db_get_setting("al_model", "hey_jarvis") or "hey_jarvis"
        idx = self._combo.findText(current)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)

        combo_row = QWidget(self)
        cr = QHBoxLayout(combo_row)
        cr.setContentsMargins(20, 0, 0, 0)
        cr.setSpacing(10)
        cr.addWidget(QLabel("Wake phrase:"))
        cr.addWidget(self._combo, 1)
        layout.addWidget(combo_row)

        self._enable.toggled.connect(combo_row.setEnabled)
        combo_row.setEnabled(self._enable.isChecked())

        layout.addStretch(1)

    def wants_download(self) -> bool:
        return HAS_OWW and self._enable.isChecked()

    def validatePage(self) -> bool:
        db_set_setting("al_enabled", "1" if self._enable.isChecked() else "0")
        db_set_setting("al_model", self._combo.currentText() or "hey_jarvis")
        return True


class _BackendRow:
    """Container for the per-backend widgets (input, test, status, model)."""
    __slots__ = ("input", "test_btn", "status", "model")
    def __init__(self):
        self.input: QLineEdit | None = None
        self.test_btn: QPushButton | None = None
        self.status: QLabel | None = None
        self.model: QComboBox | None = None


class AIBackendPage(QWizardPage):
    # Single shared signal: (backend_name, ok, msg, models)
    probe_done = Signal(str, bool, str, list)

    def __init__(self):
        super().__init__()
        self.probe_done.connect(self._on_probe_done)
        self.setTitle(" ")
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_h1("AI parsing (optional)"))
        layout.addWidget(_muted(
            "AgeniusNote can extract a title, tags, and priority from each "
            "transcript. Skip to keep raw text only. Configure later in Settings."
        ))

        self._group = QButtonGroup(self)
        current = (db_get_setting("parser_backend", "none") or "none").lower()
        self._rows: dict[str, _BackendRow] = {}

        # None
        self._rb_none = QRadioButton("None, save raw transcript only")
        self._group.addButton(self._rb_none)
        layout.addWidget(self._rb_none)

        # OpenAI
        self._rb_openai = QRadioButton("OpenAI (cloud, paid, fast)")
        self._group.addButton(self._rb_openai)
        layout.addWidget(self._rb_openai)
        self._rows["openai"] = self._build_backend_block(
            layout,
            label="OpenAI key:",
            placeholder="sk-...",
            password=True,
            existing_value=get_secret("openai"),
            model_label="Model:",
            model_placeholder="gpt-4o-mini",
            existing_model=(db_get_setting("openai_model", "") or "").strip(),
            link_html=_BACKEND_LINKS["openai"],
            backend_name="openai",
        )

        # Anthropic
        self._rb_anthropic = QRadioButton("Anthropic Claude (cloud, paid, fast)")
        self._group.addButton(self._rb_anthropic)
        layout.addWidget(self._rb_anthropic)
        self._rows["anthropic"] = self._build_backend_block(
            layout,
            label="Anthropic key:",
            placeholder="sk-ant-...",
            password=True,
            existing_value=get_secret("anthropic"),
            model_label="Model:",
            model_placeholder="claude-haiku-4-5",
            existing_model=(db_get_setting("anthropic_model", "") or "").strip(),
            link_html=_BACKEND_LINKS["anthropic"],
            backend_name="anthropic",
        )

        # Ollama
        self._rb_ollama = QRadioButton("Ollama (local, free, requires Ollama install)")
        self._group.addButton(self._rb_ollama)
        layout.addWidget(self._rb_ollama)
        self._rows["ollama"] = self._build_backend_block(
            layout,
            label="Ollama URL:",
            placeholder="http://localhost:11434",
            password=False,
            existing_value=(db_get_setting("ollama_base_url", "http://localhost:11434") or "http://localhost:11434"),
            model_label="Model:",
            model_placeholder="qwen2.5:7b-instruct-q5_K_M",
            existing_model=(db_get_setting("ollama_model", "") or "").strip(),
            link_html=_BACKEND_LINKS["ollama"],
            backend_name="ollama",
        )

        # Apply current choice
        if current == "openai":
            self._rb_openai.setChecked(True)
        elif current == "anthropic":
            self._rb_anthropic.setChecked(True)
        elif current in ("local", "ollama", "auto"):
            self._rb_ollama.setChecked(True)
        else:
            self._rb_none.setChecked(True)

        for rb in (self._rb_none, self._rb_openai, self._rb_anthropic, self._rb_ollama):
            rb.toggled.connect(lambda _on: self._sync_rows())
        self._sync_rows()

        layout.addStretch(1)

    def _build_backend_block(
        self, parent_layout, *, label, placeholder, password, existing_value,
        model_label, model_placeholder, existing_model, link_html, backend_name,
    ) -> _BackendRow:
        row = _BackendRow()

        # Row 1: input + Test
        input_row = QWidget(self)
        ir = QHBoxLayout(input_row)
        ir.setContentsMargins(20, 0, 0, 0)
        ir.setSpacing(10)
        ir.addWidget(QLabel(label))
        row.input = QLineEdit(input_row)
        row.input.setPlaceholderText(placeholder)
        if password:
            row.input.setEchoMode(QLineEdit.Password)
        if existing_value:
            row.input.setText(existing_value)
        ir.addWidget(row.input, 1)
        row.test_btn = QPushButton("Test", input_row)
        row.test_btn.setCursor(Qt.PointingHandCursor)
        row.test_btn.clicked.connect(lambda _checked=False, b=backend_name: self._run_test(b))
        ir.addWidget(row.test_btn)
        parent_layout.addWidget(input_row)

        # Row 2: status / help link
        row.status = QLabel(link_html, self)
        row.status.setOpenExternalLinks(True)
        row.status.setTextInteractionFlags(Qt.TextBrowserInteraction)
        row.status.setWordWrap(True)
        row.status.setStyleSheet(
            "color: rgba(180, 200, 230, 0.7); font-size: 12px; padding-left: 100px;"
        )
        parent_layout.addWidget(row.status)

        # Row 3: model dropdown
        model_row_w = QWidget(self)
        mr = QHBoxLayout(model_row_w)
        mr.setContentsMargins(20, 0, 0, 0)
        mr.setSpacing(10)
        mr.addWidget(QLabel(model_label))
        row.model = QComboBox(model_row_w)
        row.model.setEditable(True)
        row.model.lineEdit().setPlaceholderText(model_placeholder)
        if existing_model:
            row.model.setCurrentText(existing_model)
        mr.addWidget(row.model, 1)
        parent_layout.addWidget(model_row_w)

        return row

    def _sync_rows(self) -> None:
        # Each backend's block enabled only when its radio is selected.
        # parentWidget() of the input is the row container.
        gates = {
            "openai": self._rb_openai.isChecked(),
            "anthropic": self._rb_anthropic.isChecked(),
            "ollama": self._rb_ollama.isChecked(),
        }
        for name, row in self._rows.items():
            enabled = gates[name]
            row.input.parentWidget().setEnabled(enabled)
            row.status.setEnabled(enabled)
            row.model.parentWidget().setEnabled(enabled)

    def validatePage(self) -> bool:
        if self._rb_openai.isChecked():
            db_set_setting("parser_backend", "openai")
            set_secret("openai", self._rows["openai"].input.text().strip())
            db_set_setting("openai_model", self._rows["openai"].model.currentText().strip())
        elif self._rb_anthropic.isChecked():
            db_set_setting("parser_backend", "anthropic")
            set_secret("anthropic", self._rows["anthropic"].input.text().strip())
            db_set_setting("anthropic_model", self._rows["anthropic"].model.currentText().strip())
        elif self._rb_ollama.isChecked():
            db_set_setting("parser_backend", "local")
            db_set_setting(
                "ollama_base_url",
                self._rows["ollama"].input.text().strip() or "http://localhost:11434",
            )
            db_set_setting("ollama_model", self._rows["ollama"].model.currentText().strip())
        else:
            db_set_setting("parser_backend", "none")
        return True

    def _run_test(self, backend: str) -> None:
        row = self._rows[backend]
        value = row.input.text().strip()
        row.test_btn.setEnabled(False)
        row.test_btn.setText("Testing…")

        def worker():
            if backend == "openai":
                ok, msg, models = probe_openai(value)
            elif backend == "anthropic":
                ok, msg, models = probe_anthropic(value)
            else:  # ollama
                ok, msg, models = probe_endpoint(value or "http://localhost:11434")
            self.probe_done.emit(backend, ok, msg, models)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str, bool, str, list)
    def _on_probe_done(self, backend: str, ok: bool, msg: str, models: list) -> None:
        row = self._rows.get(backend)
        if row is None:
            return
        row.test_btn.setEnabled(True)
        row.test_btn.setText("Test")
        prefix = "✓" if ok else "✗"
        color = "#22c55e" if ok else "#f87171"
        row.status.setText(
            f'<span style="color: {color}">{prefix} {msg}</span><br>'
            f'{_BACKEND_LINKS[backend]}'
        )
        if models:
            current = row.model.currentText().strip()
            row.model.clear()
            row.model.addItems(models)
            if current and current in models:
                row.model.setCurrentText(current)
            elif current:
                row.model.setCurrentText(current)
            else:
                row.model.setCurrentIndex(0)


class DownloadsPage(QWizardPage):
    def __init__(self, wizard_ref):
        super().__init__()
        self._wizard = wizard_ref
        self._all_done = False
        self.setTitle(" ")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(_h1("Downloading models"))
        self._caption = _muted(
            "Hang tight. Fetching the speech-to-text model and wake-word "
            "files so your first mic click is instant."
        )
        layout.addWidget(self._caption)

        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)  # indeterminate during work
        layout.addWidget(self._progress)

        self._status = QLabel("Waiting…", self)
        self._status.setStyleSheet("font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px;")
        layout.addWidget(self._status)

        self._errors = QLabel("", self)
        self._errors.setWordWrap(True)
        self._errors.setStyleSheet("color: #f87171; font-size: 12px;")
        layout.addWidget(self._errors)

        layout.addStretch(1)

        self._mgr = DownloadManager(self)
        self._mgr.task_started.connect(self._on_started)
        self._mgr.task_done.connect(self._on_done)
        self._mgr.task_failed.connect(self._on_failed)
        self._mgr.all_done.connect(self._on_all_done)

    def initializePage(self) -> None:
        whisper_model = db_get_setting("whisper_model", "base.en") or "base.en"
        tasks = [{"type": "whisper", "model": whisper_model}]
        wake_page = self._wizard.page_wake
        if wake_page.wants_download():
            tasks.append({"type": "openwakeword"})

        self._status.setText("Starting…")
        self._errors.setText("")
        self._progress.setRange(0, 0)
        self._all_done = False
        self._wizard.button(QWizard.NextButton).setEnabled(False)
        self._wizard.button(QWizard.BackButton).setEnabled(False)
        self._mgr.start(tasks)

    def isComplete(self) -> bool:
        return self._all_done

    @Slot(str)
    def _on_started(self, label: str) -> None:
        self._status.setText(f"Downloading: {label}…")

    @Slot(str)
    def _on_done(self, label: str) -> None:
        self._status.setText(f"Finished: {label}")

    @Slot(str, str)
    def _on_failed(self, label: str, err: str) -> None:
        existing = self._errors.text()
        line = f"{label} failed: {err}"
        self._errors.setText(f"{existing}\n{line}".strip())

    @Slot(bool)
    def _on_all_done(self, ok: bool) -> None:
        self._all_done = True
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        if ok:
            self._status.setText("All downloads complete ✓")
        else:
            self._status.setText("Finished with errors, see below. You can retry later from Settings.")
        self._wizard.button(QWizard.NextButton).setEnabled(True)
        self._wizard.button(QWizard.BackButton).setEnabled(True)
        self.completeChanged.emit()


class DonePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle(" ")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(_h1("You're all set"))
        layout.addWidget(_muted(
            "Click Finish to start using AgeniusNote. Re-run this wizard any "
            "time from Settings → Re-run setup."
        ))
        layout.addStretch(1)


# ── Wizard ────────────────────────────────────────────────────


class SetupWizard(QWizard):
    """Run with .exec(). Returns QDialog.Accepted on Finish, Rejected on cancel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AgeniusNote, Setup")
        self.setMinimumSize(640, 520)
        self.setWizardStyle(QWizard.ModernStyle)
        icon_path = _ASSETS / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.page_welcome = WelcomePage()
        self.page_whisper = WhisperPage()
        self.page_wake = WakeWordPage()
        self.page_ai = AIBackendPage()
        self.page_downloads = DownloadsPage(self)
        self.page_done = DonePage()

        self.addPage(self.page_welcome)
        self.addPage(self.page_whisper)
        self.addPage(self.page_wake)
        self.addPage(self.page_ai)
        self.addPage(self.page_downloads)
        self.addPage(self.page_done)

        self.setButtonText(QWizard.FinishButton, "Finish")
        self.setOption(QWizard.NoBackButtonOnStartPage, True)

    def accept(self) -> None:
        db_set_setting("first_run_complete", "1")
        super().accept()

    def reject(self) -> None:
        # User hit Cancel / closed the window. Don't nag them again — they
        # can re-run from Settings if they want.
        db_set_setting("first_run_complete", "1")
        super().reject()
