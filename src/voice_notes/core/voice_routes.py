"""Voice command routing.

Detects when a transcript should be treated as a quick-todo entry instead of
going through the full note/task AI parser. Pure string logic — no DB or
network calls. Safe to use from worker threads.
"""

from __future__ import annotations

import re

# Prefixes that route to the right-pane quick-todo list. Order matters: more
# specific phrasing first so "quick todo: x" doesn't fall through to "todo: x".
# All entries are stored in normalized form (lowercase, hyphens → spaces) so
# they line up with the normalized input in try_route_to_todo().
_TODO_PREFIXES = (
    "quick todo",
    "quick to do",
    "add to my list",
    "add to the list",
    "remind me to",
    "to do",
    "todo",
)

# Strip a single leading punctuation char (",", ":", ".") and surrounding ws.
_LEADING_PUNCT = re.compile(r"^[\s,:.\-]+")
_TRAILING_PUNCT = re.compile(r"[\s.,]+$")


def try_route_to_todo(text: str) -> str | None:
    """Return the cleaned todo text if `text` starts with a quick-todo trigger.

    Returns None if no trigger matched, so the caller falls through to the
    regular note/task AI parser.

    Hyphens are normalized to spaces so Whisper transcriptions like
    "quick-to-do ..." or "to-do ..." still match. The substitution is 1:1 in
    length so character offsets into the original text stay aligned.
    """
    if not text:
        return None
    candidate = text.strip()
    normalized = candidate.lower().replace("-", " ")
    for prefix in _TODO_PREFIXES:
        if normalized.startswith(prefix):
            tail = candidate[len(prefix):]
            tail = _LEADING_PUNCT.sub("", tail)
            tail = _TRAILING_PUNCT.sub("", tail)
            if not tail:
                return None
            # Capitalize first letter for cosmetic consistency; preserve rest.
            return tail[:1].upper() + tail[1:]
    return None
