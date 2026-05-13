"""Audio recording: Recorder (push-to-talk) + RecorderVAD (silence auto-stop).

No Qt imports here. Threads call back into UI via agenius_note.ui.signals.
"""

from __future__ import annotations

import io
import threading
import time

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000  # 16 kHz mono — ideal for Whisper + openWakeWord


class Recorder:
    """Records audio from the default mic in a background thread."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.frames: list[np.ndarray] = []
        self.stream = None
        self.recording = False

    def start(self) -> None:
        self.frames = []
        self.recording = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self.stream.start()

    def _callback(self, indata, _frame_count, _time_info, _status):
        if self.recording:
            self.frames.append(indata.copy())

    def stop(self) -> bytes:
        """Stop recording and return WAV bytes."""
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if not self.frames:
            return b""
        audio = np.concatenate(self.frames, axis=0)
        buf = io.BytesIO()
        sf.write(buf, audio, self.sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()


class RecorderVAD(Recorder):
    """Recorder that fires a callback when silence is detected (VAD)."""

    def start_vad(
        self,
        on_silence,
        vad_threshold: float = 0.008,
        silence_secs: float = 1.5,
        max_secs: float = 30.0,
    ) -> None:
        self._vad_on_silence = on_silence
        self._vad_threshold = vad_threshold
        self._vad_silence_secs = silence_secs
        self._vad_max_secs = max_secs
        self._vad_fired = False
        self.start()
        self._vad_t0 = time.monotonic()
        self._vad_last_speech = time.monotonic()
        threading.Thread(target=self._vad_watch, daemon=True).start()

    def _vad_watch(self) -> None:
        # Grace period — ignore silence right after wake word
        time.sleep(0.4)
        self._vad_last_speech = time.monotonic()

        while self.recording and not self._vad_fired:
            time.sleep(0.05)
            if not self.frames:
                continue
            now = time.monotonic()

            # Hard max cap
            if now - self._vad_t0 >= self._vad_max_secs:
                self._vad_fired = True
                self._vad_on_silence()
                return

            # RMS of most recent chunk
            rms = float(np.sqrt(np.mean(self.frames[-1] ** 2)))
            if rms >= self._vad_threshold:
                self._vad_last_speech = now
            elif now - self._vad_last_speech >= self._vad_silence_secs:
                self._vad_fired = True
                self._vad_on_silence()
                return
