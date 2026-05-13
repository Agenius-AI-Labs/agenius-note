"""Background model downloader.

Pre-downloads the Whisper STT model and the openWakeWord pretrained models
so the first-run user doesn't hit a mysterious wait on the first mic click.

Emits Qt signals from a worker thread. The UI thread connects to them with
AutoConnection (which becomes QueuedConnection cross-thread).
"""

from __future__ import annotations

import threading
from typing import Iterable

from PySide6.QtCore import QObject, Signal


class DownloadManager(QObject):
    task_started = Signal(str)             # human label
    task_done    = Signal(str)             # human label
    task_failed  = Signal(str, str)        # human label, error message
    all_done     = Signal(bool)            # True if every task succeeded

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: threading.Thread | None = None

    def start(self, tasks: Iterable[dict]) -> None:
        """Kick off downloads in a daemon thread. `tasks` is a list of dicts:
        {"type": "whisper", "model": "base.en"} or {"type": "openwakeword"}.
        """
        task_list = list(tasks)
        self._thread = threading.Thread(
            target=self._run, args=(task_list,), daemon=True
        )
        self._thread.start()

    def _run(self, tasks: list[dict]) -> None:
        ok = True
        for task in tasks:
            kind = task.get("type")
            try:
                if kind == "whisper":
                    self._download_whisper(task.get("model", "base.en"))
                elif kind == "openwakeword":
                    self._download_oww()
                else:
                    raise ValueError(f"Unknown task type: {kind}")
            except Exception as exc:
                ok = False
                label = self._label_for(task)
                self.task_failed.emit(label, str(exc))
        self.all_done.emit(ok)

    def _label_for(self, task: dict) -> str:
        kind = task.get("type", "")
        if kind == "whisper":
            return f"Whisper {task.get('model', 'base.en')}"
        if kind == "openwakeword":
            return "openWakeWord"
        return kind or "task"

    def _download_whisper(self, model_name: str) -> None:
        label = f"Whisper {model_name}"
        self.task_started.emit(label)
        # Constructing WhisperModel triggers a snapshot_download from
        # Hugging Face Hub if the model isn't already cached. CPU + int8 keeps
        # the download lean and works regardless of GPU presence.
        from faster_whisper import WhisperModel
        WhisperModel(model_name, device="cpu", compute_type="int8")
        self.task_done.emit(label)

    def _download_oww(self) -> None:
        label = "openWakeWord"
        self.task_started.emit(label)
        try:
            import openwakeword.utils
        except ImportError as exc:
            raise RuntimeError(
                "openwakeword is not installed. Install via "
                "`pip install openwakeword` to enable wake-word features."
            ) from exc
        openwakeword.utils.download_models()
        self.task_done.emit(label)
