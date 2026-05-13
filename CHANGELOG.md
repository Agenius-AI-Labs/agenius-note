# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-13

First public release. Extracted from the Agenius AI Labs monorepo.

### Added
- Push-to-talk dictation in the Capture workspace with auto-save on transcription, AI parse patches title/tags/priority/type without blocking the UI.
- Active Listening with openWakeWord (built-in: `hey_jarvis`, `alexa`, `hey_mycroft`, `hey_rhasspy`). Custom `.onnx` models supported via Settings.
- Quick Note workspace: standalone scratchpad. Transcript appends per take. Copy / Clear. No DB writes.
- Quick Todos right pane: text-add or voice-route ("quick todo: ..."), checkbox + delete on hover, clear-done, collapsible.
- Voice routing: prefixes like `quick todo:`, `remind me to`, `todo:` route transcripts into the right pane instead of the AI parser.
- First-run setup wizard: pre-downloads Whisper and openWakeWord models before the user clicks the mic.
- Three themes: dark, light, cyberpunk.
- Settings dialog with link to the openWakeWord training notebook.
- Re-run setup from Settings.

### Performance
- Forced CUDA float16 path in `faster-whisper`, with graceful CPU/int8 fallback.
- VAD silence skipping (`vad_filter=True`) cuts transcription time on quiet audio.
- Status surface shows device + elapsed ms after each transcription.

### Distribution
- pyproject.toml with `voice-notes` console entry point.
- MIT license.
- Cross-platform user-data directory (`%APPDATA%`, `~/Library/Application Support`, `$XDG_DATA_HOME`).
