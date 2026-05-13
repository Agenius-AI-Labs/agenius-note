"""Font loading via QFontDatabase.

Bundles Inter (300/400/500/600/700) + JetBrains Mono (400/500) under
voice_notes/assets/fonts/. If a TTF is missing the loader falls back to the
operating system's default; never crashes.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _resource_path(rel: str) -> Path:
    """Resolve a resource path that survives PyInstaller freezing."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / rel
    return Path(__file__).resolve().parents[1] / rel


def load_fonts() -> int:
    """Register every TTF in assets/fonts/ with QFontDatabase. Returns count loaded."""
    try:
        from PySide6.QtGui import QFontDatabase
    except ImportError:
        return 0

    fonts_dir = _resource_path("assets/fonts")
    if not fonts_dir.exists():
        return 0

    loaded = 0
    for ttf in sorted(fonts_dir.glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(ttf)) >= 0:
            loaded += 1
    return loaded
