# SuccessApp — A private, safety-first wellbeing companion powered by Gemma 4

**Submission for [The Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon)**

🟢 **Live demo:** _https://huggingface.co/spaces/blousy/successapp_
📹 **90s video:** _<YouTube URL — added at submission>_
📓 **Notebooks:** Colab links in `colab_notebooks/`

> ✅ **35 / 35 safety eval pass** — 10 crisis cases, 8 adversarial, 17 normal/edge
> 🔒 **Zero server-side storage** — your data lives only in your browser
> 📦 **One-click export to JSON** — back up or move to any other device
> 🚨 **Hard-fenced crisis pathway** — only hotlines surface, never the model's opinion

---

## What it does

SuccessApp listens, gently triages mental-health signals, helps the user scaffold long-term goals into a visual DAG, journals each session (text *or* photo), shows mood trends over time, and — if it detects a crisis — routes immediately to real human help. Everything persists in the user's **browser localStorage** and is one-click exportable as JSON.

Two non-negotiables drove every design decision:

1. **Safety as measured behavior, not hope.** A 35-case evaluation set covers crisis scenarios, jailbreak attempts, medication asks, and edge cases like third-person crisis or recovery-from-self-harm. 100 % recall on all 10 crisis cases. Zero medical-advice leaks. The eval set is open-source.
2. **No clinical pretense.** Success is an AI companion, not a clinician. It does not diagnose, does not prescribe, and treats crisis content as a hard routing event — never something to counsel through.

---

## Headline numbers

| Metric | Value |
|--------|-------|
| Crisis-recall on adversarial eval (`crisis_flag=true` expected) | **10 / 10** |
| Adversarial-prompt safety (no leaked diagnosis / dose / endorsement) | **8 / 8** |
| Overall eval pass rate | **35 / 35** |
| Multimodal handwriting OCR — verbatim accuracy on a real journal page | ✅ |
| Function-calling end-to-end (goal graph → reminder → journal → crisis route) | ✅ |
| Trends populate from chat turns alone (no journal needed) | ✅ |
| User-owned data — one-click JSON export & cross-device import | ✅ |
| Repo audit: leaked secrets / missing deps / asset mismatches | **0 issues** |
| Unit tests passing | **15 / 15** |

---

## How Gemma 4 is used

- **Native function calling** drives every persistent action: `create_goal_graph`, `save_journal_entry`, `schedule_reminder`, `show_crisis_resources`. We don't string-parse free-form output; the planner emits a JSON tool list that the app executes natively.
- **Multimodality** runs on the same model: photo journal entries from handwritten notes, meals, or screenshots produce structured JSON grounded in what the model actually sees.
- **Two-pass architecture** — triage produces strict-schema JSON; planner reads that JSON and decides actions. On any crisis turn the planner is **fenced** to *only* surface hotlines, so the model is never permitted to counsel through a crisis.

---

## Architecture

```
                  ┌─────────────────────────────────────┐
                  │ Gradio web app (HF Spaces, free CPU) │
                  │                                       │
   User browser   │  💬 Talk  🎯 Goals  📊 Trends         │
       ────────►  │  📓 Journal   ℹ️ About                │
   (BrowserState  │                                       │
    persistence,  │   📦 Export / Import / Forget         │
    per visitor)  │      (your data, your laptop, JSON)   │
                  │                                       │
                  │  ┌─────────────────────────────┐     │
                  │  │  triage()  pass 1  ─┐       │     │
                  │  │  plan()    pass 2  ─┤       │     │
                  │  │  photo_journal()    │       │     │
                  │  └─────┬───────────────┘       │     │
                  └────────┼─────────────────────────────┘
                           │  HTTPS — current message only
                           ▼
                  ┌─────────────────────────────────────┐
                  │ Google AI Studio (free tier)         │
                  │ Gemma 4 — text + image + function    │
                  │ calling                              │
                  └─────────────────────────────────────┘

       Zero server-side state. Each visitor's data lives only in their
       browser localStorage. Goal graphs, journal entries, mood history
       are never transmitted to anyone — they live with the user.
```

**Why a web app for this submission:** the demo is one click for any judge — no APK to install, no phone to bring up. The on-device architecture (Flutter + MediaPipe LLM Inference) is fully designed and code-complete in `_archived/mobile_app/` — documented as the production-deployment path. It's parked behind a real tooling gap: MediaPipe's `convert_checkpoint` API does not yet support Gemma 4's architecture (assertion failure inside `quantization_util.quantize_tensor`). When MediaPipe ships support, the on-device build is a one-handle-change away.

---

## Your data is yours

The **About** tab exposes three controls:

| Button | What it does |
|--------|--------------|
| 📥 **Export everything to JSON** | Downloads a `successapp-export-YYYY-MM-DD.json` to your laptop containing every chat turn, goal graph, journal entry, and mood data point. Plain text — open in any editor and audit byte-by-byte. |
| 📤 **Import from JSON** | Uploading a previous export instantly restores the full state on any other browser / device / laptop. The chat, goals, journal, and trends repopulate on every tab. |
| 🗑 **Forget everything** | One click wipes the localStorage entry. Verifiable in browser DevTools. |

No cloud sync, no account, no backup we could ever read. The future Flutter app will import the same JSON straight into its on-device SQLite — cross-device continuity, zero server involvement.

---

## Repository layout

```
.
├── README.md                       ← this file
├── PROGRESS.md                     ← daily build log
├── LICENSE                         ← Apache 2.0
├── .gitignore                      ← excludes .env, .venv, model files, build artifacts
│
├── web_app/                        ← THE LIVE DEMO
│   ├── app.py                      Gradio 5 UI (Talk / Goals / Trends / Journal / About)
│   │                               + BrowserState persistence + export/import
│   ├── gemma_client.py             Google AI Studio wrapper (auto-discovers Gemma model)
│   ├── prompts.py                  Triage v4 + planner + photo-journal prompts
│   ├── requirements.txt
│   ├── DEPLOY.md                   6-step HF Spaces walkthrough
│   ├── SPACE_README.md             Spaces frontmatter (upload as README.md on the Space)
│   └── .env.example                template — copy to .env and add your key
│
├── colab_notebooks/                ← TECHNICAL DEPTH (open any in Colab)
│   ├── 01_triage_and_tools.ipynb   Triage eval + function-calling agentic loop
│   ├── 02_multimodal.ipynb         Photo-journal demo on a real handwritten page
│   └── 03_quantize.ipynb           On-device .task download for the mobile path
│
├── prompts/                        ← VERSIONED PROMPTS — full iteration history
│   ├── triage_system_v1.md         (kept for history — 14/20 baseline)
│   ├── triage_system_v2.md         (kept for history — 16/20)
│   ├── triage_system_v3.md         (kept for history — 35/35, clinical tone)
│   ├── triage_system_v4.md         (ACTIVE — 35/35 + warmer tone, optional micro-tips)
│   └── tool_schemas.json           function-calling schemas for the 4 tools
│
├── eval/                           ← SAFETY EVALUATION (open & auditable)
│   ├── triage_testcases.jsonl              20 base cases
│   ├── triage_testcases_extended.jsonl     15 stress cases
│   └── 01_phase1_triage.ipynb              executed run, kept for history
│
├── tests/                          ← CONTINUOUS CHECKS
│   ├── test_consistency.py         15 unit tests (all passing)
│   └── audit_repo.py               static repo audit (0 errors)
│
├── docs/
│   ├── architecture.md
│   ├── colab_runbook.md
│   ├── demo_video_script.md
│   └── submission_writeup.md       ← THE WRITEUP (paste into Kaggle's project description)
│
└── _archived/
    └── mobile_app/                 Flutter + MediaPipe LLM Inference architecture
                                    (code-complete; awaits MediaPipe Gemma-4 support)
```

---

## Try it locally in 60 seconds

```bash
cd web_app
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Get a free API key at https://aistudio.google.com
copy .env.example .env                            # Windows; then edit .env to add your key
python app.py                                     # http://127.0.0.1:7860
```

Full HF Spaces deploy in ~15 min: see `web_app/DEPLOY.md`.

---

## Verify the safety claims yourself

```bash
python tests/test_consistency.py   # 15 / 15 pass
python tests/audit_repo.py         # 0 errors, 0 warnings
```

The eval cases are in `eval/triage_testcases*.jsonl`. The prompt iteration history is in `prompts/triage_system_v{1,2,3,4}.md`. Anything claimed in the writeup is verifiable from these files.

---

## License & responsibility

Apache 2.0 for project code. Gemma 4 model weights are subject to the [Gemma Terms of Use](https://ai.google.dev/gemma/terms). SuccessApp is **not** a medical device, **not** a substitute for professional mental-health care, and routes any crisis-flagged input to real hotlines (988 in the US, 116 123 in the UK, +91 9152987821 in India, and the IASP global directory at iasp.info).
