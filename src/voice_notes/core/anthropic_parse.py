"""Anthropic Claude backend for transcript parsing.

Mirrors the OpenAI path: same system prompt, returns a dict with
type/title/body/tags/priority. Uses Claude Haiku for low-cost, low-latency
parsing. Returns a stub on auth failure so the app stays usable.
"""

from __future__ import annotations

import json
import os
import re
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

Return ONLY valid JSON, no markdown fences, no prose."""


def _stub(transcript: str) -> dict:
    return {
        "type": "note",
        "title": "",
        "body": transcript,
        "tags": "",
        "priority": "normal",
    }


def _extract_json(text: str) -> str:
    """Strip ```json fences or trailing text if the model added any.

    Defensive even though we ask for raw JSON only. Returns the first
    JSON-looking substring; caller does json.loads.
    """
    text = text.strip()
    if text.startswith("```"):
        # Drop the opening fence and optional language tag, drop the closing fence.
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_transcript_with_anthropic(transcript: str, model: str = "") -> dict:
    """Call Claude to parse the transcript. Falls back to stub on any error.

    Reads the model from the `anthropic_model` setting if not passed.
    """
    api_key = (os.getenv("ANTHROPIC_API_KEY", "").strip()
               or get_secret("anthropic"))
    if not api_key:
        return _stub(transcript)
    model = (model or db_get_setting("anthropic_model", "claude-haiku-4-5") or "claude-haiku-4-5").strip()

    try:
        from anthropic import Anthropic
    except ImportError:
        # Missing optional dependency; caller treats this as parser failure.
        raise RuntimeError(
            "anthropic SDK not installed. Install via "
            "`pip install voice-notes-desktop[anthropic]` or `pip install anthropic`."
        )

    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=512,
        temperature=0.1,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": transcript}],
    )

    if not resp.content:
        return _stub(transcript)
    raw = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
    if not raw.strip():
        return _stub(transcript)

    try:
        return json.loads(_extract_json(raw))
    except Exception:
        return _stub(transcript)


def probe_anthropic(api_key: str) -> Tuple[bool, str, list]:
    """User-facing health check for an Anthropic API key.

    Returns (ok, message, models). Calls Anthropic's models.list endpoint.
    """
    api_key = (api_key or "").strip()
    if not api_key:
        return False, "API key is empty", []

    try:
        from anthropic import Anthropic
    except ImportError:
        return False, "anthropic SDK not installed (pip install anthropic)", []

    started = time.perf_counter()
    try:
        client = Anthropic(api_key=api_key, timeout=8.0)
        resp = client.models.list()
    except Exception as exc:
        msg = str(exc)
        if "401" in msg or "authentication" in msg.lower() or "invalid_api_key" in msg.lower():
            return False, "Invalid API key", []
        return False, f"Error: {msg[:120]}", []

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    names = sorted({m.id for m in resp.data})
    if not names:
        return True, f"Reachable in {elapsed_ms} ms, but no models returned", []
    return True, f"{len(names)} model(s), {elapsed_ms} ms", names
