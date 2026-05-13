"""Local faster-whisper transcription.

Model selection is read from the SQLite settings KV (`whisper_model`).
Device selection prefers CUDA float16 (RTX 5060 etc.), falls back to CPU int8.
VAD filtering is enabled by default to skip silence and trim wall time.
"""

from __future__ import annotations

import os
import tempfile
import time

from .db import db_get_setting

_WHISPER_CACHE: dict = {"model": None, "name": "", "device": "", "compute": ""}


def _build_model(model_name: str):
    """Try CUDA first, fall back to CPU. Returns (model, device, compute_type)."""
    from faster_whisper import WhisperModel

    try:
        model = WhisperModel(model_name, device="cuda", compute_type="float16")
        return model, "cuda", "float16"
    except Exception:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        return model, "cpu", "int8"


def _get_whisper_model(model_name: str):
    cache = _WHISPER_CACHE
    if cache["model"] is None or cache["name"] != model_name:
        model, device, compute = _build_model(model_name)
        cache["model"] = model
        cache["name"] = model_name
        cache["device"] = device
        cache["compute"] = compute
    return cache["model"]


def get_device_label() -> str:
    """For status display. Empty until first transcription call."""
    if not _WHISPER_CACHE["device"]:
        return ""
    return f"{_WHISPER_CACHE['device']}/{_WHISPER_CACHE['compute']}"


def transcribe(wav_bytes: bytes) -> str:
    """Backwards-compatible: returns text only."""
    text, _meta = transcribe_with_meta(wav_bytes)
    return text


def transcribe_with_meta(wav_bytes: bytes) -> tuple[str, dict]:
    """Returns (text, {"device", "compute", "elapsed_ms", "model"})."""
    model_name = db_get_setting("whisper_model", "base.en")
    vad_setting = (db_get_setting("whisper_vad", "on") or "on").lower()
    use_vad = vad_setting in ("on", "1", "true", "yes")

    started = time.perf_counter()
    model = _get_whisper_model(model_name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name
    try:
        kwargs = {}
        if use_vad:
            kwargs["vad_filter"] = True
            kwargs["vad_parameters"] = {"min_silence_duration_ms": 500}
        try:
            segments, _info = model.transcribe(tmp_path, **kwargs)
        except TypeError:
            # Older faster-whisper without vad_filter support
            segments, _info = model.transcribe(tmp_path)
        text = " ".join(s.text.strip() for s in segments).strip()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    meta = {
        "device": _WHISPER_CACHE["device"],
        "compute": _WHISPER_CACHE["compute"],
        "elapsed_ms": elapsed_ms,
        "model": model_name,
    }
    return text, meta
