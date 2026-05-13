"""Voice-routing prefix detector.

These are pure-string tests; no DB, no Qt, no network. Cheap to run on
every PR across the matrix.
"""

from __future__ import annotations

import pytest

from agenius_note.core.voice_routes import try_route_to_todo


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Canonical forms
        ("quick todo: water the plants", "Water the plants"),
        ("todo: refactor db", "Refactor db"),
        ("remind me to call carissa", "Call carissa"),
        ("add to my list buy milk", "Buy milk"),
        ("add to the list pay rent", "Pay rent"),

        # Hyphen normalization (Whisper emits these)
        ("quick-to-do review document", "Review document"),
        ("to-do refactor db", "Refactor db"),
        ("Quick-to-do, water the plants", "Water the plants"),

        # Mixed case + punctuation
        ("Quick Todo, send Carissa the link", "Send Carissa the link"),
        ("To do, send carissa the doc", "Send carissa the doc"),

        # Trailing punctuation stripped
        ("todo: foo.", "Foo"),

        # First-letter capitalization preserved as-is for proper nouns
        ("todo: McDonalds is overrated", "McDonalds is overrated"),
    ],
)
def test_routes_match(raw, expected):
    assert try_route_to_todo(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "this is just a normal note",
        "todo:",  # empty tail
        "to-do",  # no tail
        "remind me",  # missing "to ..."
        "the to do list is full",  # prefix not at start
    ],
)
def test_routes_no_match(raw):
    assert try_route_to_todo(raw) is None
