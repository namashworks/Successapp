# SuccessApp — Flutter (Android-first)

100% on-device wellbeing companion powered by Gemma 4 (E2B-IT, int4 quantized via MediaPipe LLM Inference).

## Build prerequisites
- Flutter 3.22+
- Android Studio (with Android SDK 34, NDK 26)
- A physical Android device (recommended: 8 GB+ RAM) or Android Emulator with at least 6 GB RAM
- The quantized model file `gemma-4-e2b-it-int4.task` exported from `colab_notebooks/03_quantize.ipynb`

## Project setup
```
cd mobile_app
flutter create . --org com.successapp --platforms=android
# Re-apply our lib/ and assets/ over the generated scaffold
flutter pub get
```

> The `flutter create .` step generates Android/iOS boilerplate WITHOUT overwriting existing `lib/`, `assets/`, or `pubspec.yaml` in most Flutter versions, but verify with git diff before continuing.

## Drop in the model
```
mkdir -p android/app/src/main/assets/models
cp /path/to/gemma-4-e2b-it-int4.task android/app/src/main/assets/models/
```

## Add required permissions to `android/app/src/main/AndroidManifest.xml`
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />
```

## Run / build
```
flutter run                # debug on connected device
flutter build apk --release  # produces android/app/build/outputs/flutter-apk/app-release.apk
```

## Architecture
```
lib/
  main.dart                # bootstraps services, picks onboarding vs home
  services/
    gemma_service.dart     # wraps flutter_gemma; triage / plan / photo_journal
    storage.dart           # SQLite + SharedPreferences. All on-device.
    notifications.dart     # flutter_local_notifications schedules daily nudges
  screens/
    onboarding_screen.dart # one-time privacy pledge
    home_screen.dart       # bottom-nav: Talk / Goals / Journal
    chat_screen.dart       # main triage chat
    crisis_screen.dart     # hard-coded hotline routing
    goals_screen.dart      # GraphView rendering of goal DAGs
    journal_screen.dart    # camera-driven photo journaling
assets/
  models/                  # the .task model file lives here
  prompts/                 # triage_system_v2.txt etc — loaded at startup
```

## Privacy guarantees
- Zero network calls in production. Audit with `grep -r "http" lib/` (only allowed match: `url_launcher` opening hotline URIs).
- All conversations live in app-private SQLite (`successapp.db`). No analytics, no telemetry.
- Crisis path is offline-safe — hotline numbers and `iasp.info` are bundled.
