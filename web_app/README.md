# SuccessApp — Web App

Gradio frontend + Google AI Studio (free-tier Gemma 4) backend. Zero model weights to host.

## Run locally

```bash
cd web_app
python -m venv .venv
.venv\Scripts\activate          # Windows
# or: source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Get a key from https://aistudio.google.com -> Get API key
# Then either set the env var:
set GOOGLE_API_KEY=your_key_here    # Windows cmd
# or create web_app/.env containing:
#   GOOGLE_API_KEY=your_key_here

python app.py
```

Opens at http://localhost:7860.

## Deploy to Hugging Face Spaces (free CPU tier)

1. Create a new Space at https://huggingface.co/spaces → "Gradio" SDK
2. Upload these files: `app.py`, `gemma_client.py`, `prompts.py`, `requirements.txt`
3. In Space Settings → **Variables and secrets** → add `GOOGLE_API_KEY` as a **secret**
4. The Space auto-builds and launches. Share the URL.

## Architecture

```
Browser ── Gradio (this app) ── Google AI Studio API ── Gemma 4
              │
              ├── Triage turn       (returns JSON: category, severity, crisis_flag, goal_hint)
              ├── Crisis short-circuit if crisis_flag true → hotline screen, no further calls
              ├── Planner turn      (returns tool_calls list)
              └── Tool execution    (in-process Python; same contract as the Colab notebooks)
```

## Files
- `app.py` — Gradio UI, state machine, tool executors, goal-graph renderer
- `gemma_client.py` — Wraps Google AI Studio. Tries multiple Gemma-4 handles, falls back to Gemma 3.
- `prompts.py` — TRIAGE / PLANNER / PHOTO_JOURNAL system prompts (mirror `/prompts/triage_system_v3.md`)
- `requirements.txt` — Gradio, google-generativeai, plotting deps

## Limits (free tier)
- ~15 requests/minute, ~1000/day on Gemma 4
- For demo recording this is plenty. For production, paid tier or self-hosted is needed.
