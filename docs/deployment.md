# Deployment

Three ways to run AgeniusNote, ranked by who they're for.

## 1. Pre-built bundle (most users)

Released artifacts for each tag at `https://github.com/Agenius-AI-Labs/agenius-note/releases`.

### Windows

- File: `AgeniusNote-<version>-windows.zip` (~280-350 MB).
- Unzip and run `agenius-note.exe`. Windows SmartScreen warns because we don't have a code-signing certificate. Click "More info" then "Run anyway".
- Windows will prompt for microphone permission on first capture.
- **Uninstall:** delete the unzipped folder. Per-user data lives at `%APPDATA%\agenius-note\`.

### macOS

- File: `AgeniusNote-<version>-macos.zip` (universal arm64 + x86_64).
- Unzip and drag `agenius-note.app` into Applications.
- First launch: Gatekeeper blocks because we don't have an Apple Developer signing cert yet. Right-click the app then Open then confirm.
- macOS will prompt for microphone permission on first capture (System Settings then Privacy & Security then Microphone).
- **Uninstall:** drag the app to Trash. Per-user data lives at `~/Library/Application Support/agenius-note/`.

### Linux

- File: `AgeniusNote-<version>-linux.tar.gz` (x86_64).
- `tar -xzf AgeniusNote-*-linux.tar.gz && ./agenius-note/agenius-note`.
- Requires PulseAudio or PipeWire for mic capture (default on Ubuntu, Fedora, Arch, etc.).
- Requires `libxcb`, `libglib`, etc. Most modern distros have these pre-installed; if not, your package manager will surface the missing libs.
- **Uninstall:** delete the extracted folder. Per-user data lives at `~/.local/share/agenius-note/` (or `$XDG_DATA_HOME/agenius-note/`).

## 2. pip install (developers and Python users)

```bash
pip install agenius-note
agenius-note
```

For local development:
```bash
git clone https://github.com/Agenius-AI-Labs/agenius-note.git
cd agenius-note
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate
pip install -e ".[all,dev]"
agenius-note
```

Optional extras:
- `agenius-note[wakeword]`, adds openWakeWord (Active Listening). Default-included with `[all]`.
- `agenius-note[openai]`, adds the OpenAI client (cloud AI parsing).
- `agenius-note[anthropic]`, adds the Anthropic client (cloud AI parsing).
- `agenius-note[dev]`, adds ruff, pytest, pytest-qt, pillow (for building icons).

### Migrating from `voice-notes-desktop`

If you previously ran the project under its old name:

```bash
pip uninstall voice-notes-desktop -y
pip install -U agenius-note
```

On first launch the app copies your `voice-notes` user-data directory into the new `agenius-note` location and moves your stored OpenAI / Anthropic keys from the legacy keyring service into the new one. The legacy data dir is left in place so you can roll back if needed.

## 3. docker-compose for supporting services

The desktop app stays native. Docker is for the supporting services some users want to self-host. The most common is a local LLM via [Ollama](https://ollama.com).

```yaml
# docker-compose.yml (in the repo root, ship in a later release)
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
volumes:
  ollama-data:
```

Then in AgeniusNote then Settings then AI parsing then pick "Ollama (local)", set base URL to `http://localhost:11434`.

If you'd rather not run Docker, Ollama installs as a native app on Windows / macOS / Linux from [ollama.com](https://ollama.com). The app talks to it over HTTP either way.

## Where your data lives

| OS | Path |
|---|---|
| Windows | `%APPDATA%\agenius-note\` |
| macOS | `~/Library/Application Support/agenius-note/` |
| Linux | `$XDG_DATA_HOME/agenius-note/` (defaults to `~/.local/share/agenius-note/`) |

Override with `AGENIUS_NOTE_DATA_DIR=/some/path` if you want portable installs (e.g., on a USB drive). The legacy `VOICE_NOTES_DATA_DIR` is still honored as a fallback.

Contents:
- `agenius_note.db`, SQLite with all your notes, tasks, todos, and settings.
- WAL files alongside (created during writes, removed on close).
- `scratch/`, short-lived WAV captures, removed after each transcription.
- `agenius-note.log`, rotating app log (1 MB × 3 backups).

The Whisper model cache lives in `~/.cache/huggingface/hub/` (faster-whisper default), separate from app data. Delete it to force re-download.

## API keys

OpenAI / Anthropic API keys are stored in your OS keyring under the service name `agenius-note` (legacy entries under `voice-notes-desktop` are auto-migrated on first launch):

| OS | Backing store |
|---|---|
| Windows | Credential Manager |
| macOS | Keychain |
| Linux | Secret Service (GNOME Keyring, KWallet via D-Bus) |

If no keyring backend is available (a headless Linux box, for example), the keys fall back to the SQLite `settings` table. Read precedence in the parser modules is: environment variable then keyring then DB. Setting `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in your shell always wins.

To delete a stored key:
- macOS: open Keychain Access, find `agenius-note`, delete the entry.
- Windows: `Credential Manager` then Web Credentials or Generic Credentials then search for `agenius-note`.
- Linux: `seahorse` (GNOME Keyring GUI) or `secret-tool clear service agenius-note account openai`.

Or use the Settings dialog in the app: clear the field and Save.

## GPU acceleration (optional)

If you have an Nvidia GPU and want 10-30x faster transcription:

1. Install Nvidia drivers (most modern setups already have them).
2. Install CUDA Toolkit 12 and cuDNN 9 from [nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads).
3. Restart. Launch AgeniusNote. Status after a transcription should read `Transcribed in 423 ms (cuda/float16)`.

If you see `cpu/int8` instead, CUDA isn't reachable from Python. Common causes:
- `cudnn` DLLs not on PATH (Windows).
- CUDA Toolkit 11 instead of 12 (faster-whisper 1.x needs 12).
- Missing `libcudnn8.so` symlinks (Linux).

No GPU? You're on `cpu/int8` and that's fine for `base.en` or smaller models. On a recent laptop you'll get ~1-2x realtime, which is fine for short clips.

## AI parsing (optional)

Three options, set in Settings then AI parsing:

| Backend | Network? | Cost | Setup |
|---|---|---|---|
| None | No | Free | Default. Raw transcript saves as-is. |
| Ollama | Local only | Free | Install Ollama (native or Docker), `ollama pull llama3.2`, set base URL in Settings. |
| OpenAI | Cloud | ~$0.0001/transcript with gpt-4o-mini | Paste API key in Settings. |
| Anthropic | Cloud | ~$0.0001/transcript with Claude Haiku | Paste API key in Settings. |

`auto` mode tries Ollama first and falls back to OpenAI, then Anthropic. Good for "I want local but cloud as backup".

## Custom wake words

See [custom-wake-word.md](custom-wake-word.md). Short version: train a `.onnx` in the openWakeWord Colab notebook, drop the file path into Settings then Active Listening then Custom model file.
