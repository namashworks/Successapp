# SuccessApp — Progress Log

Competition: [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon)
Deadline: **May 18, 2026**
Today: 2026-04-17 — full submission package drafted

---

## Repo Structure

```
Kaggle competition Gemma 4/
├── README.md                        ← top-level pitch
├── PROGRESS.md                      ← this file
├── prompts/
│   ├── triage_system_v1.md          (deprecated — kept for history)
│   ├── triage_system_v2.md          (active)
│   └── tool_schemas.json
├── eval/
│   ├── triage_testcases.jsonl       (20 cases)
│   ├── triage_testcases_extended.jsonl (15 stress-test cases)
│   └── 01_phase1_triage.ipynb       (first executed run, kept for history)
├── colab_notebooks/
│   ├── 01_triage_and_tools.ipynb    (Phases 1+2 merged — self-contained)
│   ├── 02_multimodal.ipynb          (Phase 3, independent)
│   ├── 03_quantize.ipynb            (Phase 5, independent)
│   └── _deprecated/                 (00 setup notebooks kept for history)
├── mobile_app/                      (Flutter Android app)
│   ├── pubspec.yaml
│   ├── README.md
│   ├── lib/
│   │   ├── main.dart
│   │   ├── services/{gemma_service,storage,notifications}.dart
│   │   └── screens/{onboarding,home,chat,crisis,goals,journal}_screen.dart
│   └── assets/prompts/{triage_system_v2,planner_system,photo_journal_system}.txt
└── docs/
    ├── demo_video_script.md
    ├── architecture.md
    └── submission_writeup.md
```

---

## Phase status

| Phase | Status | What's done | What you must do |
|------|--------|------------|------------------|
| 0. Setup | ✅ | Model loads from Kaggle in Colab | — |
| 1. Triage (text) | ✅ | v3 prompt hits **20/20** on the eval (crisis 5/5, adversarial 4/4). DoD met. | — |
| 2. Function calling | ✅ | Demo confirmed end-to-end: goal graphs created, reminder scheduled, journal saved, crisis path intercepts and suppresses other tools. | — |
| 3. Multimodal | ✅ | Verified on a real handwritten note. Handwriting OCR nailed verbatim text. mood_score, summary, key_themes all grounded. crisis_flag correctly false on a frustration note. | — |
| 4. Expanded eval | 🟡 | 15 stress-test cases added (covers method-specific, third-person crisis, minor safety, role-swap jailbreaks, fake-authority, joke-disguised crisis, existential) | Run the extended set against v2 prompt. |
| 5. Edge deploy | 🟡 | Flutter app skeleton complete (6 screens, 3 services, 3 prompt assets). Quantization notebook drafted. | (a) Run notebook 04, download `.task`. (b) `flutter create .` over `mobile_app/`. (c) Drop `.task` into assets. (d) `flutter build apk --release`. (e) Install on a 6GB+ Android phone. |
| 6. Submission package | 🟡 | README, architecture.md, demo script, writeup all written | Record 90s video. Fill in numbers in `docs/submission_writeup.md` Section 5. Push to GitHub. Submit on Kaggle. |

---

## Daily Log

### 2026-05-15 (Day 4) — Strategic pivot: web app instead of Android
- Decision: cut the Android build, ship a Gradio web app instead. Reasons: 3 days left, Flutter install too costly (disk + learning curve), web is faster to a polished demo and lower-friction for judges.
- Architecture: Gradio frontend on HF Spaces (free CPU) + Google AI Studio API (free Gemma 4 tier) for inference. Zero hosted weights, zero server-side state.
- Mobile app archived: `_archived/mobile_app/` — code-complete Flutter scaffold kept as documented future-work path, referenced in submission writeup.
- New `web_app/` folder: `app.py`, `gemma_client.py`, `prompts.py`, `requirements.txt`, `README.md`. All Python parses cleanly. v3 prompt embedded.
- Features wired: triage chat with crisis short-circuit, planner-driven tool calls, goal-graph rendering (networkx + matplotlib), photo journal upload (multimodal), session reset, inspector panel for demo recordings.
- Updated docs: root `README.md` (web-first), `docs/submission_writeup.md` (eval table, prompt-iteration narrative, two-architecture story), `docs/demo_video_script.md` (6-scene 90s script for web app).
- 12/12 unit tests still pass, 0 audit errors after the pivot.

### 2026-05-14 (Day 3) — Phase 5 quantization: forced pivot
- Tried MediaPipe converter on Gemma 4 E2B-IT. Got `AssertionError` in `quantization_util.quantize_tensor` (`number_bits` not in {4, 8}) — the converter has no recipe for Gemma 4's per-layer embeddings or vision blocks.
- Confirmed: MediaPipe int4 converter does not yet support Gemma 4 (as of 2026-05-14).
- Decision: **Android app runs Gemma 3n E2B-IT** (predecessor edge variant with full MediaPipe support). Colab notebooks 01–02 continue to use Gemma 4 for all triage / function-calling / multimodal demos.
- Updated `colab_notebooks/03_quantize.ipynb` (model handle + filename + markdown).
- Updated `mobile_app/lib/services/gemma_service.dart` (loads `successapp-gemma3n-e2b-int4.task`).
- Documented honestly in `docs/submission_writeup.md` Section 5.
- Tests + audit clean.

### 2026-05-13 (Day 2 cont.) — Phase 3 multimodal verified
- Notebook 02 (multimodal) ran on a real handwritten journal entry (user's own).
- Handwriting OCR: verbatim extraction — "I want to become an AI engineer but getting no job and 500+ rejections" — perfect.
- Output: mood_score=3, key_themes=[career frustration, rejection, ambition], crisis_flag=false (correct — frustration without crisis-level content).
- Minor: connected_goal_hint abstracted to "career success" instead of "become an AI engineer". Acceptable; can tighten the photo prompt later.
- **Phase 3 DoD met.** Multimodal proven on the hardest case (handwritten cursive).

### 2026-05-13 (Day 2) — Phase 1 + 2 locked
- v3 prompt run end-to-end: **20/20 eval pass**. Every crisis case caught, every adversarial case refused, no medical-advice or diagnosis leaks, no pipe-joined enums.
- Phase 2 function-calling demo: all 4 tools fired correctly (create_goal_graph x2, schedule_reminder, save_journal_entry). Crisis path: only show_crisis_resources fires.
- Goal-graph render verified via matplotlib in step 8 ("Pivot to Product Manager role — 180 days").
- Date hallucination fixed in tool stub (notebook) and chat_screen.dart (Flutter).
- **Phase 1 + Phase 2 DoD met. Proceeding to Phase 3 (multimodal).**

### 2026-04-17 (Day 1) — first run + v2
- Phase 0 audit: model loads from Kaggle, ~10 GB VRAM on T4.
- Phase 1 first run: **14/20** eval pass. Crisis recall 4/5. Medical-advice leak. Goal-hint weak.
- Security incident: Kaggle API token leaked into notebook source code. Token rotated, file scrubbed.
- v2 prompt written: enumerates crisis triggers (A–E), hardens medical refusal, fixes goal extraction.
- All Phase 2–6 deliverables drafted: function-calling notebook, multimodal notebook, extended eval, Flutter app (6 screens, 3 services), quantization notebook, README, architecture, demo script, submission writeup.

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Quantization quality drops triage scores below target | Run Phase 1 eval against the int4 model in Colab before shipping; fall back to int8 (~5 GB) if needed |
| `flutter_gemma` plugin API drift | Pin to a known-working version in `pubspec.yaml`; MediaPipe CLI fallback documented in notebook 04 |
| Goal-graph DAG produces cycles | Validate `_validate_args` in Phase 2 + add cycle check before saving |
| Crisis screen routes work offline (judges test airplane mode) | All hotline numbers and `iasp.info` URL are hardcoded in `crisis_screen.dart` — no network needed |
| Submission rules require iOS too | Current scope is Android only; if rules clarify iOS is required, repurpose Flutter codebase via Mac build later |

---

## Definition of done for SUBMISSION

- [ ] Phase 1 eval ≥ 80% overall AND 100% crisis recall on the combined 35-case set
- [ ] Phase 2 demo turns produce one valid goal graph, one journal entry, one reminder, and one crisis interception
- [ ] Phase 3 demo handles a real handwritten photo and one workout photo with valid JSON
- [ ] APK builds and runs offline on a real Android phone
- [ ] Demo video <= 90 sec recorded, uploaded unlisted, linked in writeup
- [ ] GitHub repo public with this README
- [ ] Kaggle submission form filled with: repo URL, video URL, write-up (paste from `docs/submission_writeup.md`)
