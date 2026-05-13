# Architecture

A tour of the moving parts. Read this before touching code that crosses threads, hits the DB, or wires new signals.

## Layers

```
agenius_note/
├── core/           # No Qt imports. Pure logic + I/O.
│   ├── audio.py        Mic capture (push-to-talk Recorder, VAD-stopping RecorderVAD)
│   ├── stt.py          faster-whisper wrapper; CUDA→CPU fallback; VAD filter; timing meta
│   ├── ai_parse.py     Routes transcripts to Ollama or OpenAI; returns structured JSON
│   ├── ollama_parse.py Local Ollama backend
│   ├── tts.py          ElevenLabs playback (optional, not exposed in default UI)
│   ├── wakeword.py     openWakeWord listener thread; resolves built-in names or file paths
│   ├── voice_routes.py Prefix detector: "quick todo: ..." → quick_todos route
│   ├── downloads.py    Background model downloader for the setup wizard
│   └── db.py           SQLite schema + CRUD: voice_items, quick_todos, settings
├── theme/          # Visual tokens + QSS template renderer
│   ├── tokens.py       3 palettes: dark, light, cyberpunk
│   ├── qss_template.py string.Template-driven stylesheet
│   └── fonts.py        Inter + JetBrains Mono loader
├── ui/             # PySide6 widgets only
│   ├── signals.py      AppSignals (cross-thread bus)
│   ├── main_window.py  Sidebar + stack + right pane; AL state machine
│   ├── sidebar.py      Left nav (4 workspaces + AL toggle)
│   ├── capture_panel.py    Voice → AI-parsed note/task form
│   ├── quick_note_panel.py Voice → raw scratchpad
│   ├── list_panel.py       Tasks / Notes list views
│   ├── quick_todos_panel.py Right-side todo pane
│   ├── al_status_bar.py    State badge above the main stack
│   ├── settings_dialog.py  All persisted settings + Re-run setup
│   ├── setup_wizard.py     First-run model download wizard
│   └── widgets/            Shared small components
└── assets/         Icons, fonts, generated PNGs
```

## Threading model

This is the easy thing to get wrong, so it's spelled out:

- **GUI thread** owns every widget mutation. Anything that touches `QWidget.set...()` runs here.
- **Worker threads** (`threading.Thread(daemon=True)`) own:
  - Audio capture (`Recorder`, `RecorderVAD`).
  - Wake-word listening (`WakeWordListener`).
  - Whisper transcription (`transcribe_with_meta()`).
  - AI parse calls (`parse_transcript_with_ai()`).
  - Model downloads (`DownloadManager`).
- **Workers never touch widgets.** They emit Qt signals on `AppSignals` (or local `Signal` objects on their parent widget). Qt's `AutoConnection` promotes cross-thread emits to `QueuedConnection`, marshalling the slot call back to the GUI thread.

If you find yourself wanting to call `self._label.setText(...)` from a worker, stop. Define a signal, emit from worker, connect slot on GUI side.

## Signal bus

`ui/signals.py::AppSignals` is the cross-thread message bus. One instance lives on `MainWindow.signals`; widgets that need to listen take a reference.

```
recording_started ()
recording_tick    (float)
transcription_done (str)
transcription_error (str)
parse_done (dict, str)   # parsed_json, raw_transcript
al_ready / al_state_changed / al_error / al_wakeword_hit / al_recording_done / al_cycle_complete
items_changed (str)      # 'task' | 'note' | 'all'
quick_todos_changed ()
theme_changed (str)
```

Special parse_done payloads:
- `{"_error": "..."}` — parser failed; capture panel falls back to raw transcript.
- `{"_routed_todo": "..."}` — transcript was routed to the quick-todos pane instead of becoming a note. Capture panel shows "Added to todos: ..." status and skips DB write.

## Active Listening state machine

```
idle
  → loading        (wake-word model loading)
  → listening      (mic open, waiting for trigger)
  → wake-detected  (score above threshold; ~220ms grace before recording)
  → recording      (RecorderVAD running, auto-stops on silence)
  → transcribing   (Whisper running in worker thread)
  → parsing        (AI parse running in worker thread)
  → idle (cycle complete; restart listener)
```

`MainWindow._al_*` slots own the state. The `ALStatusBar` widget mirrors the state visually. Each transition flips the sidebar status dot and the AL bar colour via QSS `[state="..."]` selectors.

## Push-to-talk flow (Capture workspace)

1. User clicks the mic. `CapturePanel._start_recording()` starts `Recorder`, kicks the tick timer, flips QSS recording state.
2. User clicks again. `_stop_recording()` spawns the worker thread.
3. Worker calls `transcribe_with_meta(wav)`. Result is `(text, meta)`; meta has `device`, `compute`, `elapsed_ms`, `model`.
4. Worker checks `try_route_to_todo(text)`. If matched: insert quick todo, emit `parse_done({"_routed_todo": text})`, return.
5. Otherwise emit `transcription_done(text)`. Capture panel paints body **immediately** and auto-saves (so a slow parse doesn't lose the transcript).
6. Worker calls `parse_transcript_with_ai(text)`. Emit `parse_done(parsed, raw)`.
7. GUI patches title / tags / priority / type. Re-runs `_auto_save()` to persist.

## DB schema

SQLite WAL mode, single file in the user-data directory (see [Deployment](deployment.md) for the path).

```sql
voice_items (
  id INTEGER PRIMARY KEY,
  item_type TEXT CHECK (item_type IN ('note','task')),
  title TEXT, body TEXT,
  status TEXT CHECK (status IN ('open','done')),
  priority TEXT CHECK (priority IN ('low','normal','high')),
  due_at TEXT, tags TEXT,           -- tags is JSON array
  source TEXT, created_at TEXT, updated_at TEXT
)
quick_todos (
  id INTEGER PRIMARY KEY,
  text TEXT, done INTEGER,
  source TEXT CHECK (source IN ('typed','voice')),
  created_at TEXT, completed_at TEXT
)
settings (key TEXT PRIMARY KEY, value TEXT)
```

Migrations are not yet implemented; `init_db()` uses `CREATE TABLE IF NOT EXISTS`. Schema is additive-only for v0.x.

## QSS / theming

`theme/qss_template.py` is one big `string.Template` with `$token` interpolation. `theme/tokens.py` defines three palettes; `render()` substitutes them.

Dynamic state is driven by Qt property selectors (`QFrame#alStatusBar[state="listening"] { ... }`). Setting the property doesn't restyle automatically — call `helpers.restyle(widget)` after `setProperty()`.

## Where data lives

| Item | Location |
|---|---|
| SQLite DB | `<user-data>/agenius-note/agenius_note.db` |
| Whisper model cache | `~/.cache/huggingface/hub/` (faster-whisper default) |
| openWakeWord models | `<openwakeword>/resources/models/` (pip-installed location) |
| Settings | inside the SQLite `settings` table, not on disk separately |

`<user-data>` resolves to `%APPDATA%` (Windows), `~/Library/Application Support` (macOS), or `$XDG_DATA_HOME` / `~/.local/share` (Linux).
