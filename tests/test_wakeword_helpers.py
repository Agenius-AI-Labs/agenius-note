"""Wake-word helpers (pure logic, no openwakeword dependency)."""

from __future__ import annotations

from pathlib import Path

from agenius_note.core.wakeword import display_label_for, _looks_like_path


def test_looks_like_path_extensions():
    assert _looks_like_path("/path/to/foo.onnx") is True
    assert _looks_like_path("foo.tflite") is True
    assert _looks_like_path("FOO.ONNX") is True


def test_looks_like_path_separators():
    assert _looks_like_path("dir/name") is True
    assert _looks_like_path("dir\\name") is True


def test_looks_like_path_builtin_names():
    assert _looks_like_path("hey_jarvis") is False
    assert _looks_like_path("alexa") is False
    assert _looks_like_path("") is False


def test_display_label_for_builtin():
    assert display_label_for("hey_jarvis") == "hey_jarvis"


def test_display_label_for_path():
    # File stem only; no directory or extension.
    assert display_label_for("/tmp/hey_biggie.onnx") == "hey_biggie"
    assert display_label_for("C:\\models\\customword.tflite") in {"customword", "C:\\models\\customword"}
    # Above tolerates Path semantics on each OS; on Windows the backslashes
    # are real separators, on POSIX they're literal filename chars.


def test_display_label_for_empty():
    assert display_label_for("") == "hey_jarvis"
