# civic_navigator_dvcqg

Basic implementation per `PROJECT_REQUIREMENTS.md`.

## What’s included

- FastAPI backend: `GET /health`, `WS /ws/{session_id}` with conversation-first agent loop, memory context, UI sync gate, screenshot + highlight tool hooks.
- Chrome extension (MV3 side panel): Vietnamese chat UI, progress bar, “Xong rồi” shortcut, hard handoff overlay, screenshot capture relay, highlight overlay injection.

## Run (dev)

1. Backend: see `backend/README_DEV.md`
2. Extension: see `extension/src/panel/README_DEV.md`
