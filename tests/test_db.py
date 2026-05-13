"""Schema + CRUD smoke tests for the SQLite layer.

Uses the isolated_data_dir fixture so each test gets a fresh DB.
"""

from __future__ import annotations

import pytest


def test_init_creates_tables(isolated_data_dir):
    db = isolated_data_dir
    # init_db ran in the fixture; verify a known table exists by inserting.
    row = db.db_create("note", "hello", "world", "normal", ["tag1"], "typed")
    assert row["id"] > 0
    assert row["item_type"] == "note"
    assert row["title"] == "hello"


def test_db_list_filter_by_type(isolated_data_dir):
    db = isolated_data_dir
    db.db_create("note", "n1", "body", "normal", [], "typed")
    db.db_create("task", "t1", "body", "high", ["urgent"], "typed")
    notes = db.db_list(item_type="note")
    tasks = db.db_list(item_type="task")
    assert len(notes) == 1 and notes[0]["title"] == "n1"
    assert len(tasks) == 1 and tasks[0]["title"] == "t1"


def test_db_update_rejects_unknown_column(isolated_data_dir):
    db = isolated_data_dir
    row = db.db_create("note", "x", "y", "normal", [], "typed")
    # Defense-in-depth: must refuse column names not in the allowlist.
    with pytest.raises(ValueError):
        db.db_update(row["id"], {"item_type; DROP TABLE": "evil"})


def test_db_update_allows_whitelisted_column(isolated_data_dir):
    db = isolated_data_dir
    row = db.db_create("note", "x", "y", "normal", [], "typed")
    updated = db.db_update(row["id"], {"title": "renamed"})
    assert updated is not None
    assert updated["title"] == "renamed"


def test_quick_todos_crud(isolated_data_dir):
    db = isolated_data_dir
    a = db.qt_create("buy milk", source="typed")
    b = db.qt_create("walk dogs", source="voice")
    assert db.qt_count_open() == 2

    db.qt_toggle(a["id"])
    assert db.qt_count_open() == 1

    cleared = db.qt_clear_done()
    assert cleared >= 1
    assert db.qt_count_open() == 1  # b still open

    assert db.qt_delete(b["id"]) is True
    assert db.qt_count_open() == 0


def test_settings_kv_roundtrip(isolated_data_dir):
    db = isolated_data_dir
    db.db_set_setting("favorite_color", "blue")
    assert db.db_get_setting("favorite_color", "default") == "blue"
    assert db.db_get_setting("nonexistent", "fallback") == "fallback"
