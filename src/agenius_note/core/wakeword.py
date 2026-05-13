"""WakeWordListener — always-on hotword detection via openWakeWord.

Lifted verbatim from voice_notes_desktop_v2.py lines 318–430.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

from .audio import SAMPLE_RATE

try:
    import openwakeword  # noqa: F401
    HAS_OWW = True
except ImportError:
    HAS_OWW = False


def get_oww_models() -> list[str]:
    """Return sorted list of available openWakeWord pretrained model names."""
    if not HAS_OWW:
        return ["hey_jarvis"]
    try:
        paths = openwakeword.utils.get_pretrained_model_paths()
        names = sorted({Path(p).stem for p in paths} - {"melspectrogram", "embedding_model"})
        return names if names else ["hey_jarvis"]
    except Exception:
        return ["hey_jarvis", "alexa", "hey_mycroft", "hey_rhasspy"]


def _looks_like_path(value: str) -> bool:
    """True when the value should be loaded as a file path instead of a name."""
    if not value:
        return False
    lower = value.lower()
    if lower.endswith((".onnx", ".tflite")):
        return True
    return "/" in value or "\\" in value


def resolve_model_arg(model_value: str) -> str:
    """Return the value to pass to OWWModel(wakeword_models=[...]).

    For built-in names (e.g. "hey_jarvis") openwakeword resolves internally.
    For file paths we pass the absolute path so custom-trained models work.
    """
    if not model_value:
        return "hey_jarvis"
    if _looks_like_path(model_value):
        return str(Path(model_value).expanduser().resolve())
    return model_value


def display_label_for(model_value: str) -> str:
    """UI-friendly label. Falls back to file stem for custom models."""
    if not model_value:
        return "hey_jarvis"
    if _looks_like_path(model_value):
        return Path(model_value).stem
    return model_value


class WakeWordListener:
    """Runs openWakeWord in a daemon thread, monitoring the mic continuously.

    When the configured score threshold is exceeded the `on_wakeword` callback
    is invoked (from the listener thread — emit a Qt signal in the callback to
    hop back to the GUI thread).

    A per-trigger cooldown prevents re-firing for `cooldown_secs` after each
    detection.
    """

    CHUNK_SAMPLES = 1280  # 80 ms @ 16 kHz — openWakeWord's expected frame size

    def __init__(
        self,
        model_name: str,
        on_wakeword,
        on_error=None,
        on_ready=None,
        score_threshold: float = 0.5,
        cooldown_secs: float = 3.0,
    ):
        self._model_name = model_name
        self._on_wakeword = on_wakeword
        self._on_error = on_error
        self._on_ready = on_ready
        self._score_threshold = score_threshold
        self._cooldown_secs = cooldown_secs
        self._running = False
        self._last_trigger = 0.0
        self.error: str | None = None

    def start(self) -> None:
        self._running = True
        self.error = None
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._running = False

    def _run(self) -> None:
        try:
            import openwakeword.utils
            from openwakeword.model import Model as OWWModel
            # Download pretrained ONNX models on first run (no-op if already cached)
            openwakeword.utils.download_models()
            arg = resolve_model_arg(self._model_name)
            oww = OWWModel(wakeword_models=[arg])
        except Exception as exc:
            err = str(exc)
            self.error = err
            if self._on_error:
                self._on_error(err)
            return

        # Model loaded — notify UI so it can go green
        if self._on_ready:
            self._on_ready()

        buf: list[np.ndarray] = []
        buf_n = 0

        def cb(indata, _frames, _t, _status):
            nonlocal buf, buf_n
            if not self._running:
                return
            chunk = (indata[:, 0] * 32767.0).astype(np.int16)
            buf.append(chunk)
            buf_n += len(chunk)

            while buf_n >= self.CHUNK_SAMPLES:
                combined = np.concatenate(buf)
                to_process = combined[: self.CHUNK_SAMPLES]
                leftover = combined[self.CHUNK_SAMPLES :]
                buf = [leftover] if len(leftover) else []
                buf_n = len(leftover)

                now = time.monotonic()
                if now - self._last_trigger > self._cooldown_secs:
                    try:
                        preds = oww.predict(to_process)
                        for _, score in preds.items():
                            if score >= self._score_threshold:
                                self._last_trigger = now
                                self._on_wakeword()
                                break
                    except Exception:
                        pass

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=512,
                callback=cb,
            ):
                while self._running:
                    time.sleep(0.05)
        except Exception as exc:
            self.error = str(exc)
