# Security Audit, v2 (post-rename + post-feature pass)

Date: 2026-05-13
Scope: changes since `bce2b35` (the v1 audit baseline) through HEAD before
the v0.2.0 tag. Focus is new attack surface introduced by:

- The voice-notes-desktop → agenius-note rename (data dir + keyring migrations).
- Anthropic Claude Haiku as a third LLM backend.
- Focus-based Active Listening routing into the Quick Note panel.
- Application-scoped hotkeys (Ctrl+Shift+Space, Ctrl+Shift+L, Ctrl+1..3).
- Right-column QSplitter (Todos/Quick Note).
- Test-connection + model-dropdown UX added to all three LLM backends.

Auditor: Claude Code agent under Michael Frostbutter direction.

This is a delta audit. The v1 baseline (`docs/security-audit-v1.md`) still
applies for everything it covered. v1 findings are not re-evaluated here
except where the rename touched their code path.

## Summary

| Severity | Count | Status |
|---|---|---|
| Critical | 0 | , |
| High | 0 | , |
| Medium | 0 | , |
| Low | 1 | Patched this pass |
| Informational | 8 | , |

`pip-audit --strict` against `requirements.lock.txt` returns **No known
vulnerabilities found** (no transitive CVEs at the pinned versions as of
this audit).

No new attack surface above the v1 baseline. The two migration paths,
keyring-service rename and data-dir copy, are the only places handling
disk + secrets contents in a new way. Both are now hardened.

## Low

### A1, legacy data-dir migration followed symlinks
**Severity:** Low
**Status:** Patched this pass.

`core/db.py::_migrate_legacy_data_dir` was calling
`shutil.copytree(entry, dest, dirs_exist_ok=True)` with default symlink
handling. The legacy directory is the user's own (`<base>/voice-notes/`)
so any attacker with write access to it already has user-account control.
But a symlink planted there could have made copytree mirror arbitrary
paths into the new data dir on first launch. Practical impact tiny; cost
of refusing symlinks is zero.

**Fix this pass:**
- Bail early if the legacy dir itself is a symlink.
- Skip per-entry symlinks (file and directory).
- Pass `symlinks=False, ignore_dangling_symlinks=True` to `copytree`.
- Surface `OSError` failures on stderr so a user debugging "where did my
  data go?" can find the reason (previously swallowed silently).

## Informational

### I1, keyring legacy-service migration is correct
`core/keystore.py::migrate_legacy_service` iterates over the known account
allowlist (`openai`, `anthropic`, `elevenlabs`), copies each from
`voice-notes-desktop` into `agenius-note`, and deletes the legacy entry
after a successful copy. Idempotent: if the new entry already exists, the
legacy one is dropped without overwriting. No account name comes from
user input.

`get_secret` falls through to the legacy service on read so the migration
window doesn't strand the user. The fallthrough is a no-op once the
migration completes.

### I2, Anthropic backend mirrors the OpenAI security posture
`core/anthropic_parse.py` reads the API key with the same precedence as
OpenAI (env, then keystore). Response is `json.loads` of a text block;
no `eval`/`exec` surface. `probe_anthropic` truncates SDK error messages
to 120 chars before surfacing in the UI (defensive against accidental
secret-in-error-message bleed). Catches `Exception` broadly, which is
appropriate for a UI-facing probe.

### I3, Hotkeys are scoped, not global
`MainWindow._wire_shortcuts` registers `QShortcut`s with
`setContext(Qt.ApplicationShortcut)`. They fire only when the
AgeniusNote window owns input focus; the OS doesn't see them. No system
keyhook surface. Sequences are hardcoded literals, never built from user
input.

### I4, Right-column splitter handles no untrusted state
`QSplitter` orientation and sizes are persisted to the `settings` table
as integers via `db_set_setting`. Read back as ints with default
fallback. No deserialization of arbitrary text.

### I5, Ollama base URL is a user-trust boundary, not SSRF
The Ollama URL field accepts user input. The traditional SSRF model
(attacker-controlled URL coerces a privileged server) does not apply
here, this is a desktop client running with the user's own privileges.
The practical risk is "user is tricked into pasting a malicious URL and
their transcripts go somewhere they didn't want." That is a phishing /
social-engineering concern, not a code defect. Documented in
`docs/deployment.md`. No code change.

If the user configures a remote Ollama endpoint over plain HTTP,
transcripts travel in cleartext. Recommend HTTPS or a tunnelled local
endpoint for remote setups, but not enforced.

### I6, Model downloads use upstream-verified channels
- Whisper: `faster_whisper.WhisperModel(...)` triggers a
  `huggingface_hub.snapshot_download`. HF Hub uses HTTPS + per-file
  SHA verification via `huggingface_hub`. Trust delegated to the library.
- openWakeWord: `openwakeword.utils.download_models()` pulls from the
  project's GitHub Releases over HTTPS. No app-layer checksum; trust
  delegated to the library. v1's M2 still applies for custom `.onnx`
  files the user supplies; README warning remains in place.

### I7, Quick Todo voice-route prefixes are literal
`core/voice_routes.py::try_route_to_todo` matches against a hardcoded
prefix list and applies a deterministic transform on the tail (strip,
capitalize first letter, drop trailing punctuation). No regex compiled
from user input.

### I8, Same anti-patterns absent across the new code paths
Re-ran the v1 audit greps over everything touched since v1:
```
grep -nE 'eval|exec|os\.system|subprocess|pickle\.|shell=True|__import__' src/agenius_note/
grep -nE 'execute\(' src/agenius_note/core/db.py
grep -nE 'api_key|API_KEY|password|token|secret' src/agenius_note/
grep -nE 'requests\.|httpx\.|urlopen|http://|https://' src/agenius_note/
grep -nE 'tempfile|NamedTemporaryFile' src/agenius_note/
```
No new eval/exec/subprocess. No new SQL string interpolation. No new
network endpoints beyond the user-configured Ollama / OpenAI / Anthropic
/ ElevenLabs hosts. Tempfile usage unchanged from v1 (still in the
user-data `scratch/` directory).

## Carry-over from v1

| ID | Severity | Status |
|---|---|---|
| H1 keyring | High | Patched in v1. Confirmed still in effect post-rename; service-name migration covered. |
| H2 LAN IP leak | High | Patched in v1. No reintroduction. |
| M1 SQL column allowlist | Medium | Patched in v1. No new callers of `db_update`. |
| M2 custom .onnx | Medium | Documented in v1. README warning still in place. Recommend pin-bumping onnxruntime if/when a CVE drops. |
| M3 lockfile + pip-audit | Medium | Patched in v1. CI still runs `pip-audit --strict` and lockfile-in-sync. This pass: `pip-audit` returns clean. |
| L1 tempfile location | Low | Patched in v1. |
| L2 print → logging | Low | Patched in v1. |
| L3 ElevenLabs voice_id URL-encode | Low | Patched in v1. |

## Patches landed this pass

1. **A1 fix:** `core/db.py::_migrate_legacy_data_dir` refuses symlinks
   (top-level and per-entry), passes `symlinks=False,
   ignore_dangling_symlinks=True` to `copytree`, and writes failures to
   stderr instead of swallowing them.

## Open follow-ups (post-v0.2.0)

- Pin `onnxruntime` minimum version explicitly in `pyproject.toml`
  optional `[wakeword]` extra once a relevant CVE lands. Today's lockfile
  is clean.
- Consider an explicit HTTPS warning if the user enters an `http://`
  Ollama URL that isn't `localhost` or `127.0.0.1`.
- Long-term: SHA-pinned lockfile (`pip-compile --generate-hashes`) so
  `--disable-pip` in CI can replace `--no-deps`.

## Audit reproducibility

```bash
# Re-run the patterns this audit used. From repo root:
rg -n 'eval|exec|os\.system|subprocess|pickle\.|shell=True|__import__' src/
rg -n 'execute\(|sqlite3' src/agenius_note/core/db.py
rg -n 'api_key|API_KEY|password|token|secret' src/
rg -n 'requests\.|httpx\.|urlopen|http://|https://' src/
rg -n 'tempfile|NamedTemporaryFile' src/
rg -n 'shutil\.(copy|move|rmtree)' src/
rg -n 'QShortcut|QKeySequence' src/
pip-audit --requirement requirements.lock.txt --strict --no-deps
```
