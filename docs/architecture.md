# SuccessApp — Architecture (archived Flutter path)

> ⚠️ **This document describes the on-device Flutter + MediaPipe LLM Inference architecture in `_archived/mobile_app/`.**
> That codebase is parked behind a known MediaPipe tooling gap (Gemma 4 quantization not yet supported) — see the writeup Section 10.
> **For the live shipping architecture (Gradio web app + Google AI Studio API), see [`docs/submission_writeup.md`](submission_writeup.md) Section 4 and the architecture diagram in the root [`README.md`](../README.md).**

## Runtime data flow (Flutter / on-device)

```
USER TYPES MESSAGE
        │
        ▼
┌─────────────────┐
│  ChatScreen     │
│  (Flutter)      │
└────────┬────────┘
         │ String userText
         ▼
┌─────────────────────────────┐
│  GemmaService.triage()      │
│   apply triage_system_v2    │
│   → on-device inference     │
│   → extract JSON            │
└────────┬────────────────────┘
         │ Map<String,dynamic> triage
         ▼
   crisis_flag?
    ┌───┴───┐
   YES      NO
    │        │
    ▼        ▼
┌─────────┐ ┌──────────────────────────┐
│ Crisis  │ │ GemmaService.plan()      │
│ Screen  │ │  apply planner_system    │
└─────────┘ │  → tool_calls JSON       │
            └──────────┬───────────────┘
                       │ list of tool calls
                       ▼
            ┌─────────────────────┐
            │  Tool dispatcher    │
            │  (chat_screen.dart) │
            └──────────┬──────────┘
                       │
            ┌──────────┼──────────┬──────────────┐
            ▼          ▼          ▼              ▼
       create_goal save_journal schedule_   show_crisis_
        _graph     _entry       reminder    resources
            │          │          │              │
            ▼          ▼          ▼              ▼
        SQLite     SQLite    OS Notifications  CrisisScreen
       goal_graphs journal_  flutter_local_      route
                  entries    notifications
```

## Files at runtime

```
/data/data/com.successapp/
├── databases/successapp.db          # journals, goals, reminders
└── shared_prefs/                    # onboarding flag

assets in APK (read-only):
├── models/gemma-4-e2b-it-int4.task  # ~3 GB
└── prompts/
    ├── triage_system_v2.txt
    ├── planner_system.txt
    └── photo_journal_system.txt
```

## Threading model

- `GemmaService` calls block the calling Dart isolate.
  - In production, wrap with `compute()` or run via an `Isolate` to keep UI smooth — the chat screen already shows a `LinearProgressIndicator` while busy.
- `flutter_local_notifications.zonedSchedule` uses Android's AlarmManager — survives app kill.

## Failure modes & mitigations

| Failure | Mitigation |
|---------|-----------|
| Model fails to load on low-RAM device | Catch in `main()`, show a "device unsupported" screen with download link to a remote-fallback waitlist |
| JSON parse fails | `_extractJson` returns null, UI shows a "could not understand, try again" snackbar |
| Crisis routing misses | Defense in depth: triage prompt enumerates triggers, planner has a hard rule, app has its own keyword fallback in chat_screen (TODO: add regex check on raw output) |
| Notification permission denied | App still functions; in-app reminder list still visible |

## Privacy contract (audited automatically in CI ideally)

- No imports of `http`, `dio`, `socket_io`, `firebase_*`, `amplitude_*` anywhere in `lib/`.
- The only `url_launcher` call goes to crisis hotline `tel:` URIs and `iasp.info`.
- No analytics SDKs in `pubspec.yaml`.
