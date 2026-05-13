"""Logging setup for the app.

Writes to:
  - stderr (so terminal users see errors)
  - <user-data>/agenius-note.log (rotated at 1 MB, 3 backups)

Level controlled by $AGENIUS_NOTE_LOG_LEVEL (or legacy $VOICE_NOTES_LOG_LEVEL).
Default: INFO.

Never log API keys, WAV bytes, or full transcripts. The few currently-
logged messages are init failures with no sensitive data.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from .db import _user_data_dir

_CONFIGURED = False


def configure() -> None:
    """Idempotent. Call once at startup."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    level_name = (
        os.environ.get("AGENIUS_NOTE_LOG_LEVEL")
        or os.environ.get("VOICE_NOTES_LOG_LEVEL")
        or "INFO"
    ).upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger("agenius_note")
    root.setLevel(level)
    root.propagate = False

    stderr = logging.StreamHandler()
    stderr.setLevel(level)
    stderr.setFormatter(fmt)
    root.addHandler(stderr)

    try:
        log_path = _user_data_dir() / "agenius-note.log"
        fh = RotatingFileHandler(
            str(log_path), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        fh.setLevel(level)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError:
        # Can't write the log file (read-only home, permissions, etc.).
        # Stderr handler still works.
        pass


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"agenius_note.{name}")
