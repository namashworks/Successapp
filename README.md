# SuccessApp — A private, safety-first wellbeing companion powered by Gemma 4

**Submission for [The Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon) · Health track**

🟢 **Live demo:** _<HF Spaces URL — added at submission>_
📹 **90s video:** _<YouTube URL — added at submission>_
📓 **Notebooks:** Colab links in `colab_notebooks/`

---

## What it does

SuccessApp listens, gently triages mental-health signals, helps the user scaffold long-term goals into a visual graph, journals each session, and — if it detects a crisis — routes immediately to real human help. It's built with two non-negotiables:

1. **Safety as measured behavior, not hope.** A 35-case evaluation set covers crisis scenarios, jailbreak attempts, medication asks, and edge cases like third-person crisis or recovery-from-self-harm. 100% recall on all 10 crisis cases. Zero medical-advice leaks. The eval set is open-source.
2. **No clinical pretense.** Success is an AI companion, not a clinician. It does not diagnose, does not prescribe, and treats crisis content as a hard routing event — never something to counsel through.

---

## Headline numbers

| Metric | Value |
|--------|-------|
| Crisis-recall on adversarial eval (`crisis_flag=true` expected) | **10 / 10** |
| Adversarial-prompt safety (no leaked diagnosis / dose / endorsement) | **8 / 8** |
| Overall eval pass rate | **35 / 35** |
| Multimodal handwriting OCR — verbatim accuracy on a real journal page | ✅ |
| Function-calling end-to-end (goal graph → reminder → journal save) | ✅ |
| Code review: leaked secrets, missing pubspec deps, asset references | **0 issues** |

---

## How Gemma 4 is used

- **Native function calling** drives every persistent action: `create_goal_graph`, `save_journal_entry`, `schedule_reminder`, `show_crisis_resources`. We don't string-parse free-form output; the planner emits a JSON tool list that the app executes natively.
- **Multimodality** runs on the same model: photo journal entries from handwritten notes, meals, and screenshots produce structured JSON grounded in what the model actually sees.
- **Two-pass architecture** — triage produces a strict-schema JSON; planner reads that JSON and decides actions. On any crisis turn the planner is fenced to *only* surface hotlines, so the model is never permitted to counsel through a crisis.

---

## Architecture

```
                ┌─────────────────────────────────────┐
                │  Gradio web app (HF Spaces, CPU)    │
   User browser │  • Triage chat                      │
        ───────►│  • Goal graph (networkx + mpl)      │
                │  • Photo journaling                 │
                │  • Crisis screen with offline       │
                │    hotlines (988, 116-123, iCall,   │
                │    iasp.info)                       │
                └──────────┬──────────────────────────┘
                           │  API
                           ▼
                ┌─────────────────────────────────────┐
                │  Google AI Studio (free-tier)       │
                │  Gemma 4 — text + multimodal +      │
                │  native function calling            │
                └─────────────────────────────────────┘
```

**Why a web app for this submission:** the demo is one click for any judge. No APK to install, no phone to bring up. The on-device architecture (Flutter + MediaPipe LLM Inference) is fully designed and code-complete in `_archived/mobile_app/` — documented as the production-deployment path. It moved to `_archived/` because MediaPipe's `convert_checkpoint` API does not yet support Gemma 4 quantization (assertion failure in `quantization_util.quantize_tensor`); we use Google's pre-quantized Gemma 3n LiteRT for that path as documented in `docs/submission_writeup.md`.

---

## Repository layout

```
.
├── README.md                       ← this file
├── PROGRESS.md                     ← daily build log
│
├── web_app/                        ← THE LIVE DEMO
│   ├── app.py                      Gradio UI (chat / goals / journal / about)
│   ├── gemma_client.py             Google AI Studio wrapper
│   ├── prompts.py                  Triage v3 + planner + photo-journal prompts
│   ├── requirements.txt
│   └── README.md
│
├── colab_notebooks/                ← TECHNICAL DEPTH (run any in Colab)
│   ├── 01_triage_and_tools.ipynb   Triage eval + function-calling agentic loop
│   ├── 02_multimodal.ipynb         Photo-journal demo on Gemma 4
│   └── 03_quantize.ipynb           On-device .task download for the mobile path
│
├── prompts/                        ← VERSIONED PROMPTS
│   ├── triage_system_v1.md         (deprecated, kept for history)
│   ├── triage_system_v2.md         (deprecated, kept for history)
│   ├── triage_system_v3.md         (active — used by web app + notebook 01)
│   └── tool_schemas.json
│
├── eval/                           ← SAFETY EVALUATION
│   ├── triage_testcases.jsonl              (20 base cases)
│   ├── triage_testcases_extended.jsonl     (15 stress cases)
│   └── 01_phase1_triage.ipynb              (executed run, kept for history)
│
├── docs/
│   ├── architecture.md
│   ├── colab_runbook.md
│   ├── demo_video_script.md
│   └── submission_writeup.md
│
├── tests/                          ← CONTINUOUS CHECKS
│   ├── test_consistency.py         (12 unit tests, all passing)
│   └── audit_repo.py               (static repo audit, 0 errors)
│
└── _archived/
    └── mobile_app/                 ← Flutter+MediaPipe production path (future work)
```

---

## Try it locally in 60 seconds

```bash
cd web_app
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Get a free API key at https://aistudio.google.com
set GOOGLE_API_KEY=AIza...

python app.py   # opens http://localhost:7860
```

Full deploy instructions (Hugging Face Spaces) are in `web_app/README.md`.

---

## License & responsibility

Apache 2.0 for project code. Gemma 4 weights are subject to the [Gemma Terms of Use](https://ai.google.dev/gemma/terms). SuccessApp is **not** a medical device, **not** a substitute for professional mental-health care, and routes any crisis-flagged input to real hotlines.
