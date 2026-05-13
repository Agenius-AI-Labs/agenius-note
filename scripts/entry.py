"""PyInstaller entry shim.

PyInstaller expects a single script file as the build target, not a module.
This shim just imports and runs `voice_notes.__main__:main`. Keeping it tiny
makes the frozen entry stable across packaging tweaks.
"""

from __future__ import annotations

import sys

from voice_notes.__main__ import main


if __name__ == "__main__":
    sys.exit(main())
