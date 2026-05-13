"""Shared pytest fixtures.

Most importantly: redirect the user-data dir to a per-test tmp_path before
agenius_note.core.db is imported, so tests don't touch the real DB.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Point AGENIUS_NOTE_DATA_DIR at a fresh dir and reload core.db.

    Also disables the real OS keyring so keystore tests exercise the DB
    fallback path. Without this, the developer's actual Keychain /
    Credential Manager entries leak into test results.
    """
    monkeypatch.setenv("AGENIUS_NOTE_DATA_DIR", str(tmp_path))
    # Also clear the legacy env var so the back-compat path doesn't win.
    monkeypatch.delenv("VOICE_NOTES_DATA_DIR", raising=False)
    # Force re-import of db so it picks up the new env var.
    import importlib
    import agenius_note.core.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    # Force keystore into DB-fallback mode for deterministic tests.
    import agenius_note.core.keystore as ks_mod
    importlib.reload(ks_mod)
    monkeypatch.setattr(ks_mod, "_KEYRING", None, raising=False)
    monkeypatch.setattr(ks_mod, "_KEYRING_OK", False, raising=False)
    yield db_mod
    # No teardown — tmp_path is cleaned by pytest.
