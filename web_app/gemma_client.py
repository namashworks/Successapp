"""Gemma 4 client via Google AI Studio (free tier).

Set GOOGLE_API_KEY environment variable (get a key at https://aistudio.google.com).
Free-tier quota covers hackathon-grade demo usage.
"""
import os
import json
import re
from typing import Optional
import google.generativeai as genai
from PIL import Image

from prompts import TRIAGE_SYSTEM, PLANNER_SYSTEM, PHOTO_JOURNAL_SYSTEM

# --- Configuration ----------------------------------------------------------

_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not _API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY is not set. Get a key at https://aistudio.google.com "
        "and set the env var (or put it in a .env file)."
    )
genai.configure(api_key=_API_KEY)

# Gemma model selection. Rather than hard-coding handles (which rename across API
# versions), we ASK the API which models the current key can use and pick the best
# Gemma variant available. Hard-coded candidate list remains as a fallback in case
# list_models() errors.
_MODEL_CANDIDATES_FALLBACK = [
    "gemma-3-27b-it",
    "gemma-3-12b-it",
    "gemma-3-4b-it",
    "gemma-3-1b-it",
]

_model = None
_model_name = None


def _score_gemma(name: str) -> int:
    """Higher score = more preferred. Prefers Gemma 4, then 3; instruction-tuned;
    larger variants; multimodal handles."""
    n = name.lower()
    if "gemma" not in n:
        return -1
    score = 0
    if "gemma-4" in n: score += 1000
    elif "gemma-3" in n: score += 500
    elif "gemma-2" in n: score += 200
    if "-it" in n: score += 50      # instruction-tuned (chat)
    if "vision" in n: score += 30   # multimodal preferred
    # Prefer larger param count when available (rough heuristic via the number after 'gemma-N-')
    import re
    m = re.search(r"gemma-\d+-(\d+)b", n)
    if m:
        score += int(m.group(1))    # e.g. 27b adds 27
    return score


def _discover_model_name() -> Optional[str]:
    """Ask the Google AI Studio API which Gemma models this key can use."""
    try:
        usable = []
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" not in methods:
                continue
            name = m.name.replace("models/", "")
            score = _score_gemma(name)
            if score > 0:
                usable.append((score, name))
        if not usable:
            return None
        usable.sort(reverse=True)
        return usable[0][1]
    except Exception as e:
        print(f"[gemma_client] discovery failed: {type(e).__name__}: {e}")
        return None


def _get_model():
    global _model, _model_name
    if _model is not None:
        return _model

    # 1) Try API-side discovery
    discovered = _discover_model_name()
    if discovered:
        _model = genai.GenerativeModel(discovered)
        _model_name = discovered
        print(f"[gemma_client] discovered model: {discovered}")
        return _model

    # 2) Fall back to hard-coded candidates
    last_err = None
    for name in _MODEL_CANDIDATES_FALLBACK:
        try:
            m = genai.GenerativeModel(name)
            # Probe with a trivial call to confirm the handle works
            _ = m.generate_content("ok", generation_config=genai.GenerationConfig(max_output_tokens=1))
            _model = m
            _model_name = name
            print(f"[gemma_client] fallback model: {name}")
            return m
        except Exception as e:
            last_err = e
            print(f"[gemma_client] fallback {name} failed: {type(e).__name__}")
            continue
    raise RuntimeError(
        f"No usable Gemma model found on your Google AI Studio account. "
        f"Last error: {last_err}. Run:  "
        f"python -c \"import google.generativeai as g; g.configure(api_key='YOUR_KEY'); "
        f"[print(m.name) for m in g.list_models() if 'gemma' in m.name.lower()]\""
    )


def model_name() -> str:
    _get_model()
    return _model_name or "(unloaded)"


# --- JSON extraction --------------------------------------------------------

def _extract_json(raw: str) -> Optional[dict]:
    """Pull the first balanced {...} JSON object out of the model's reply."""
    if not raw:
        return None
    raw = raw.strip()
    # Try markdown-fenced JSON first
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        cand = m.group(1)
    else:
        s, e = raw.find("{"), raw.rfind("}")
        if s == -1 or e <= s:
            return None
        cand = raw[s : e + 1]
    try:
        obj = json.loads(cand)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


# --- Core call wrappers -----------------------------------------------------

def _generate(parts: list, system: str, max_tokens: int = 512) -> str:
    """Run one inference. `parts` is a list of strings or PIL images."""
    model = _get_model()
    # Gemma via Google AI Studio doesn't support a separate system role in all paths,
    # so we prepend the system prompt to the user content.
    user_text = parts[0] if isinstance(parts[0], str) else ""
    other_parts = parts[1:] if isinstance(parts[0], str) else parts
    full = f"{system}\n\n[USER]\n{user_text}"
    contents = [full] + list(other_parts)
    response = model.generate_content(
        contents,
        generation_config=genai.GenerationConfig(
            temperature=0.0, max_output_tokens=max_tokens
        ),
    )
    return response.text or ""


def triage(user_text: str, history: Optional[list] = None) -> dict:
    """Phase-1 triage. Returns the parsed JSON dict (or a safe default on parse failure)."""
    history_blob = ""
    if history:
        history_blob = "\n[CONVERSATION SO FAR]\n" + "\n".join(history) + "\n[CURRENT TURN]\n"
    raw = _generate([f"{history_blob}{user_text}"], TRIAGE_SYSTEM, max_tokens=400)
    parsed = _extract_json(raw)
    if parsed is None:
        # Fail-safe: assume non-crisis, ask user to rephrase. Never crash the UI.
        return {
            "acknowledgment": "I'm here. Could you tell me a little more about what's going on?",
            "detected_signals": [],
            "likely_category": "unclear",
            "severity_signal": "low",
            "follow_up_question": "What feels most pressing right now?",
            "goal_hint": None,
            "crisis_flag": False,
            "_raw": raw,
        }
    return parsed


def plan(triage_json: dict, conversation_summary: str) -> dict:
    user = (
        f"TRIAGE={json.dumps(triage_json)}\n"
        f"CONVERSATION:\n{conversation_summary}"
    )
    raw = _generate([user], PLANNER_SYSTEM, max_tokens=600)
    parsed = _extract_json(raw) or {"reasoning": "(parse fail)", "tool_calls": []}
    parsed.setdefault("tool_calls", [])
    return parsed


def photo_journal(image: Image.Image, caption: str = "") -> dict:
    user_text = caption.strip() or "(no caption — describe what's meaningful in this image for wellbeing journaling)"
    raw = _generate([user_text, image], PHOTO_JOURNAL_SYSTEM, max_tokens=400)
    parsed = _extract_json(raw)
    if parsed is None:
        return {
            "summary": "Could not parse the model's response. The image may be unsupported.",
            "detected_text": "",
            "mood_score": 5,
            "key_themes": [],
            "connected_goal_hint": None,
            "crisis_flag": False,
            "_raw": raw,
        }
    return parsed
