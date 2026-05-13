# Security Policy

## Reporting a vulnerability

Please do not file a public GitHub issue for security problems. Use [GitHub Security Advisories](https://github.com/Agenius-AI-Labs/voice-notes-desktop/security/advisories/new) to report privately, or email `security@ageniuslabs.com`.

Include:
- Affected version (output of `pip show voice-notes-desktop` or the installer filename)
- OS and Python version
- Steps to reproduce
- Impact assessment (what an attacker could do)
- Suggested fix if you have one

We aim to acknowledge within 72 hours and ship a patch within 14 days for high-severity issues. Coordinated disclosure: we credit you in the release notes unless you ask otherwise.

## What's in scope

- Code execution from a malicious wake-word model file
- Path traversal or symlink attacks via the custom-model file path setting
- SQL injection in the local SQLite store
- Memory disclosure through malformed audio input
- Insecure handling of the OpenAI API key (e.g. logged to plain text)
- Auto-update code (when we add it in a future release)

## What's out of scope

- Bugs that require local administrative access to exploit
- Vulnerabilities in upstream dependencies (`PySide6`, `faster-whisper`, `openwakeword`, etc.) — please report those to the respective projects. We will pin or patch our side once they ship a fix.
- Social-engineering or phishing scenarios where the user is tricked into installing a malicious build that's not from our official Releases page.
- The unsigned-installer Gatekeeper / SmartScreen warning (we know; we don't have a code-signing cert yet).

## Supported versions

| Version | Status |
|---|---|
| 0.1.x | Supported (current) |
| < 0.1 | Not supported |

Security patches land on the latest `0.x` minor only during the v0.x series. Once v1.0 ships we'll keep the previous minor patched for 6 months.
