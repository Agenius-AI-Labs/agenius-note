"""Single QObject hub for cross-thread UI updates.

Worker threads (Recorder, RecorderVAD, WakeWordListener, TTS playback) only
ever call `signals.<name>.emit(...)`. Qt routes the slot invocation onto the
GUI thread automatically (default Qt.AutoConnection becomes QueuedConnection
for cross-thread emits). This replaces every `app.after(0, ...)` in v2.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    # Push-to-talk lifecycle
    recording_started   = Signal()
    recording_tick      = Signal(float)        # elapsed seconds
    transcription_done  = Signal(str)          # raw text
    transcription_error = Signal(str)
    parse_done          = Signal(dict, str)    # parsed_json, raw_transcript

    # Active Listening lifecycle
    al_ready            = Signal(str)          # model name
    al_state_changed    = Signal(str)          # idle | loading | listening | wake-detected | recording | transcribing
    al_error            = Signal(str)
    al_wakeword_hit     = Signal()
    al_recording_done   = Signal(bytes)        # wav payload
    al_cycle_complete   = Signal()             # transcription/parse cycle done — restart listener

    # TTS
    playback_started    = Signal(int)          # item id
    playback_done       = Signal(int)
    playback_error      = Signal(int, str)

    # Data
    items_changed       = Signal(str)          # task | note | all
    quick_todos_changed = Signal()             # quick_todos table mutated
    voices_loaded       = Signal(list)

    # Theme
    theme_changed       = Signal(str)          # dark | light
