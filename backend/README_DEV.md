# Backend dev

## Run

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r backend/requirements.txt`
3. `uvicorn backend.main:app --reload --port 8000`

## Env

Optional (enables LLM + search):

```bash
export OPENROUTER_API_KEY=...
export TAVILY_API_KEY=...
export OPENROUTER_MODEL=google/gemini-2.0-flash-001
```

If keys are not set, the backend falls back to a demo plan for “Gia hạn hộ chiếu”.
