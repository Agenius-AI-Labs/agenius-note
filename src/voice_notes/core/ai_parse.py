"""Transcript parser; dispatches between local Ollama, OpenAI, and Anthropic.

Backend choice (setting `parser_backend`):
    local      → Ollama only; raises on failure.
    openai     → OpenAI only.
    anthropic  → Anthropic Claude only.
    auto       → Try Ollama first; on any error, fall through to OpenAI then
                 Anthropic (whichever has a key).
    none       → Skip parsing, return raw transcript as body.

Default is `auto` so the app prefers local models but stays useful when the
local stack is offline.
"""

from __future__ import annotations

import os

from .anthropic_parse import parse_transcript_with_anthropic
from .db import db_get_setting
from .keystore import get_secret
from .ollama_parse import parse_transcript_locally
from .openai_parse import parse_transcript_with_openai


def _stub(transcript: str) -> dict:
    return {"type": "note", "title": "", "body": transcript, "tags": "", "priority": "normal"}


def parse_transcript_with_ai(transcript: str) -> dict:
    backend = (db_get_setting("parser_backend", "auto") or "auto").lower()
    ollama_model = db_get_setting("ollama_model", "")
    ollama_url = db_get_setting("ollama_base_url", "")

    if backend == "none":
        return _stub(transcript)

    if backend == "openai":
        try:
            return parse_transcript_with_openai(transcript)
        except Exception:
            return _stub(transcript)

    if backend == "anthropic":
        try:
            return parse_transcript_with_anthropic(transcript)
        except Exception:
            return _stub(transcript)

    if backend == "local":
        try:
            return parse_transcript_locally(transcript, model=ollama_model, base_url=ollama_url)
        except Exception:
            return _stub(transcript)

    # backend == "auto" or anything unrecognised:
    # Try local first, then OpenAI if its key is reachable, then Anthropic.
    try:
        return parse_transcript_locally(transcript, model=ollama_model, base_url=ollama_url)
    except Exception:
        pass
    openai_key = (os.getenv("OPENAI_API_KEY", "").strip()
                  or get_secret("openai"))
    if openai_key:
        try:
            return parse_transcript_with_openai(transcript)
        except Exception:
            pass
    anthropic_key = (os.getenv("ANTHROPIC_API_KEY", "").strip()
                     or get_secret("anthropic"))
    if anthropic_key:
        try:
            return parse_transcript_with_anthropic(transcript)
        except Exception:
            pass
    return _stub(transcript)
