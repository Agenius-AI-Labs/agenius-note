"""Shared pytest fixtures.

Most importantly: redirect the user-data dir to a per-test tmp_path before
voice_notes.core.db is imported, so tests don't touch the real DB.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Point VOICE_NOTES_DATA_DIR at a fresh dir and reload core.db."""
    monkeypatch.setenv("VOICE_NOTES_DATA_DIR", str(tmp_path))
    # Force re-import of db so it picks up the new env var.
    import importlib
    import voice_notes.core.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    yield db_mod
    # No teardown — tmp_path is cleaned by pytest.
