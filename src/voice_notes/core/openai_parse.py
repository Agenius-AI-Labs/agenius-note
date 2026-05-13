"""OpenAI Chat Completions backend for transcript parsing.

Mirrors anthropic_parse.py. Same system prompt, same output shape, same
graceful stub-on-failure. Default model is gpt-4o-mini for cost / latency.
"""

from __future__ import annotations

import json
import os
import time
from typing import Tuple

from .db import db_get_setting
from .keystore import get_secret


_SYSTEM_PROMPT = """Parse the following voice transcript into structured note/task data.
Return a JSON object with these fields:
- type: "note" or "task" (default "note")
- title: a short descriptive title (generate one from the content if not explicitly stated)
- body: the main content/body text (everything that isn't a field directive)
- tags: comma-separated relevant tags (infer from context if not explicitly stated)
- priority: "low", "normal", or "high" (default "normal")

The user may explicitly say things like "title is ...", "tags are ...", "priority is high",
"this is a task". They may also just speak naturally; in that case generate a concise title,
put everything in the body, infer 1-3 relevant tags, and infer priority from urgency cues.

Return ONLY valid JSON, no markdown fences."""


def _stub(transcript: str) -> dict:
    return {
        "type": "note",
        "title": "",
        "body": transcript,
        "tags": "",
        "priority": "normal",
    }


def _resolve_api_key() -> str:
    return (os.getenv("OPENAI_API_KEY", "").strip()
            or get_secret("openai"))


def parse_transcript_with_openai(transcript: str, model: str = "") -> dict:
    """Call OpenAI Chat Completions to parse the transcript.

    Falls back to stub on any error. Reads the model from the
    `openai_model` setting if not passed.
    """
    api_key = _resolve_api_key()
    if not api_key:
        return _stub(transcript)
    chosen_model = (model or db_get_setting("openai_model", "gpt-4o-mini") or "gpt-4o-mini").strip()

    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "openai SDK not installed. Install via "
            "`pip install voice-notes-desktop[openai]` or `pip install openai`."
        )

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return _stub(transcript)


def probe_openai(api_key: str) -> Tuple[bool, str, list]:
    """User-facing health check for an OpenAI API key.

    Returns (ok, message, chat_models). `chat_models` is filtered to the
    chat-completions models that make sense as parser backends.
    """
    api_key = (api_key or "").strip()
    if not api_key:
        return False, "API key is empty", []

    try:
        from openai import OpenAI
    except ImportError:
        return False, "openai SDK not installed (pip install openai)", []

    started = time.perf_counter()
    try:
        client = OpenAI(api_key=api_key, timeout=8.0)
        resp = client.models.list()
    except Exception as exc:
        # OpenAI SDK raises auth errors as AuthenticationError, etc. The
        # message text is good enough for inline display.
        msg = str(exc)
        if "401" in msg or "Incorrect API key" in msg or "invalid_api_key" in msg.lower():
            return False, "Invalid API key", []
        return False, f"Error: {msg[:120]}", []

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    all_names = sorted({m.id for m in resp.data})
    # Heuristic filter: keep gpt-*, o1*, o3*, o5* / gpt-5 models that look
    # chat-capable; drop audio / image / embedding / TTS / realtime variants.
    drop_substrings = ("audio", "realtime", "image", "tts", "transcribe",
                       "embedding", "moderation", "instruct", "edit", "search")
    chat_models = [
        n for n in all_names
        if (n.startswith("gpt-") or n.startswith("o1") or n.startswith("o3")
            or n.startswith("o5") or n.startswith("gpt5"))
        and not any(s in n for s in drop_substrings)
    ]
    if not chat_models:
        return True, (
            f"Reachable in {elapsed_ms} ms, but no chat-capable models found "
            f"(saw {len(all_names)} total). Check your account access."
        ), []
    return True, f"{len(chat_models)} chat model(s), {elapsed_ms} ms", chat_models
