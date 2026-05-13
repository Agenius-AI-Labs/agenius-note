"""Entry point for `python -m agenius_note` and the `agenius-note` console script."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_env() -> None:
    """Load OPENAI_API_KEY / ELEVENLABS_API_KEY before any core module reads them.

    Search order (first wins per key, python-dotenv's default):
      1. Current working directory `.env`
      2. User config dir `~/.config/agenius-note/.env` (Linux/Mac) or
         `%APPDATA%\\agenius-note\\.env` (Windows).
      3. Legacy pre-rename location (`voice-notes`) for back-compat.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    candidates: list[Path] = [Path.cwd() / ".env"]
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "agenius-note" / ".env")
            candidates.append(Path(appdata) / "voice-notes" / ".env")
    else:
        candidates.append(Path.home() / ".config" / "agenius-note" / ".env")
        candidates.append(Path.home() / ".config" / "voice-notes" / ".env")

    for path in candidates:
        try:
            if path.exists():
                load_dotenv(path, override=False)
        except OSError:
            continue


def _enable_high_dpi() -> None:
    """Set Qt HiDPI attributes BEFORE QApplication is constructed."""
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        if hasattr(Qt, "AA_EnableHighDpiScaling"):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass


def main() -> int:
    _load_env()
    _enable_high_dpi()

    from agenius_note.core.logging_config import configure, get_logger
    configure()
    log = get_logger("main")

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("AgeniusNote")
    app.setOrganizationName("Agenius AI Labs")

    pkg_dir = Path(__file__).resolve().parent
    icon_path = pkg_dir / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Load bundled fonts (Inter + JetBrains Mono).
    try:
        from agenius_note.theme import load_fonts
        load_fonts()
    except Exception as exc:
        log.warning("font loading failed: %s", exc)

    # Apply theme. Default first-launch to cyberpunk; honour persisted choice.
    try:
        from agenius_note.core.db import init_db, db_get_setting
        init_db()
        theme_name = db_get_setting("theme_v3", "cyberpunk") or "cyberpunk"
    except Exception:
        theme_name = "cyberpunk"

    # One-shot migrations:
    #   - copy pre-rename keyring entries (`voice-notes-desktop`) into the new
    #     service (`agenius-note`), then drop the legacy ones
    #   - push any DB-stored API keys into the OS keyring
    # Both are idempotent and silent when there's nothing to do.
    try:
        from agenius_note.core.keystore import migrate_db_to_keyring, migrate_legacy_service
        legacy = migrate_legacy_service()
        if legacy:
            log.info("migrated %d secret(s) from legacy keyring service", legacy)
        migrated = migrate_db_to_keyring()
        if migrated:
            log.info("migrated %d secret(s) from DB to OS keyring", migrated)
    except Exception as exc:
        log.warning("keyring migration skipped: %s", exc)

    try:
        from agenius_note.theme import get_theme, render
        app.setStyleSheet(render(get_theme(theme_name)))
    except Exception as exc:
        log.warning("theme apply failed: %s", exc)

    # First-run setup wizard runs before MainWindow so model downloads
    # happen up-front instead of on the first mic click.
    try:
        from agenius_note.core.db import db_get_setting as _get
        if (_get("first_run_complete", "0") or "0") != "1":
            from agenius_note.ui.setup_wizard import SetupWizard
            wiz = SetupWizard()
            wiz.exec()
    except Exception as exc:
        log.warning("setup wizard failed: %s", exc)

    from agenius_note.ui.main_window import MainWindow
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
