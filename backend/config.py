from __future__ import annotations

import os


def _getenv(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v or default


OPENROUTER_API_KEY = _getenv("OPENROUTER_API_KEY")
# print(OPENROUTER_API_KEY)
TAVILY_API_KEY = _getenv("TAVILY_API_KEY")
# print(TAVILY_API_KEY)

OPENROUTER_BASE_URL = _getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = _getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
#OPENROUTER_MODEL = _getenv("OPENROUTER_MODEL", "qwen/qwen3.6-flash")

# Extension assumes local dev backend.
SERVER_TITLE = _getenv("SERVER_TITLE", "Civic Navigator")
SERVER_REFERER = _getenv("SERVER_REFERER", "https://civic-navigator.local")

# Session retention after websocket disconnect (seconds)
SESSION_TTL_SECONDS = int(_getenv("SESSION_TTL_SECONDS", "600") or "600")
