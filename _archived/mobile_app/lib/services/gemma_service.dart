// VERIFY-BEFORE-SHIPPING:
//   The `flutter_gemma` plugin API surface has shifted across 0.5 → 0.6 → 0.7 → 0.8 → 0.9.
//   The code below targets the 0.9.x conventions (createChat / addQueryChunk / generateChatResponse).
//   After `flutter pub get`, run:
//     flutter analyze
//   If it reports method-not-found for `createChat`, `Message`, or `generateChatResponse`,
//   open the installed package's README under .pub-cache/hosted/pub.dev/flutter_gemma-*/
//   and replace the four annotated sites below.

import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_gemma/flutter_gemma.dart';

class GemmaService {
  GemmaService._();
  static final GemmaService instance = GemmaService._();

  InferenceModel? _model;
  String? _triageSystem;
  String? _plannerSystem;
  String? _photoJournalSystem;
  bool _loaded = false;

  bool get isLoaded => _loaded;

  Future<void> loadModel() async {
    // 1. Read prompt assets — these MUST exist in pubspec under `flutter: assets:`.
    _triageSystem =
        await rootBundle.loadString('assets/prompts/triage_system_v3.txt');
    _plannerSystem =
        await rootBundle.loadString('assets/prompts/planner_system.txt');
    _photoJournalSystem =
        await rootBundle.loadString('assets/prompts/photo_journal_system.txt');

    // 2. Initialise the model. The .task file is bundled under
    //    android/app/src/main/assets/models/gemma-4-e2b-it-int4.task
    final gemma = FlutterGemmaPlugin.instance;

    // VERIFY-SITE #1: installModelFromAsset is the 0.9.x name. Older versions
    // exposed setModelPath / installModel. Pick one that exists.
    // Phone runs Gemma 3n E2B (MediaPipe doesn't yet support Gemma 4 int4 quantization).
    // The Colab notebooks still showcase Gemma 4 — see docs/submission_writeup.md.
    await gemma.modelManager.installModelFromAsset(
      'models/successapp-gemma3n-e2b-int4.task',
    );

    // VERIFY-SITE #2: createModel signature (supportImage flag is 0.9.x).
    _model = await gemma.createModel(
      modelType: ModelType.gemmaIt,
      maxTokens: 2048,
      preferredBackend: PreferredBackend.gpu,
      supportImage: true,
    );
    _loaded = true;
  }

  // --- Text turn (triage, planner) -------------------------------------------

  Future<String> _runText(String system, String userText) async {
    final model = _model;
    if (model == null) throw StateError('Model not loaded');

    // VERIFY-SITE #3: createChat / addQueryChunk / generateChatResponse names.
    final chat = await model.createChat(temperature: 0.0);
    await chat.addQueryChunk(Message(text: '$system\n\nUSER:\n$userText', isUser: true));
    final response = await chat.generateChatResponse();
    return response;
  }

  Future<Map<String, dynamic>?> triage(String userText) async {
    final raw = await _runText(_triageSystem!, userText);
    return _extractJson(raw);
  }

  Future<Map<String, dynamic>?> plan(
      Map<String, dynamic> triageJson, String conversationSummary) async {
    final raw = await _runText(_plannerSystem!,
        'TRIAGE=${jsonEncode(triageJson)}\nCONVERSATION:\n$conversationSummary');
    return _extractJson(raw);
  }

  // --- Image turn (photo journal) --------------------------------------------

  Future<Map<String, dynamic>?> photoJournal(
      String imagePath, String caption) async {
    final model = _model;
    if (model == null) throw StateError('Model not loaded');

    final bytes = await File(imagePath).readAsBytes();
    final prompt = '$_photoJournalSystem\n\nUSER:\n${caption.isEmpty ? "(no caption)" : caption}';

    // VERIFY-SITE #4: generateResponse(prompt, image) is the 0.9.x one-shot
    // multimodal API. If your version uses chat-based image messages instead,
    // build a chat and pass Message(text, isUser, image: bytes).
    final raw = await model.generateResponse(prompt: prompt, image: bytes);
    return _extractJson(raw);
  }

  // --- Robust JSON extraction (handles markdown fences + stray prose) --------

  Map<String, dynamic>? _extractJson(String raw) {
    final trimmed = raw.trim();
    // 1. Try markdown-fenced JSON
    final fence = RegExp(r'```(?:json)?\s*(\{.*?\})\s*```', dotAll: true)
        .firstMatch(trimmed);
    final candidate =
        fence?.group(1) ?? _firstBalancedObject(trimmed);
    if (candidate == null) return null;
    try {
      final parsed = jsonDecode(candidate);
      if (parsed is Map<String, dynamic>) return parsed;
      return null;
    } catch (_) {
      return null;
    }
  }

  String? _firstBalancedObject(String s) {
    final start = s.indexOf('{');
    if (start == -1) return null;
    var depth = 0;
    for (var i = start; i < s.length; i++) {
      if (s[i] == '{') depth++;
      if (s[i] == '}') {
        depth--;
        if (depth == 0) return s.substring(start, i + 1);
      }
    }
    return null;
  }
}
