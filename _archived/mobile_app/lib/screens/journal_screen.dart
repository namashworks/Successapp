import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/storage.dart';
import '../services/gemma_service.dart';

class JournalScreen extends StatefulWidget {
  const JournalScreen({super.key});
  @override
  State<JournalScreen> createState() => _JournalScreenState();
}

class _JournalScreenState extends State<JournalScreen> {
  List<Map<String, dynamic>> _entries = [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final e = await Storage.listJournal();
    setState(() => _entries = e);
  }

  Future<void> _addFromPhoto() async {
    final picker = ImagePicker();
    final shot = await picker.pickImage(source: ImageSource.camera, imageQuality: 80);
    if (shot == null) return;
    setState(() => _busy = true);
    try {
      final caption = await _captionDialog() ?? '';
      final parsed = await GemmaService.instance.photoJournal(shot.path, caption);
      if (parsed == null) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not journal this photo.')));
        return;
      }
      final entry = {
        'date': DateTime.now().toIso8601String().substring(0, 10),
        'mood_score': parsed['mood_score'] ?? 5,
        'key_themes': parsed['key_themes'] ?? [],
        'wins': [],
        'concerns': [],
        'goal_progress_notes': parsed['connected_goal_hint'] ?? '',
        'reflection_prompt_for_tomorrow': "What did today's image remind you of?",
        'source': 'photo',
        'summary': parsed['summary'] ?? '',
      };
      await Storage.saveJournal(entry);
      await _load();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<String?> _captionDialog() async {
    final ctrl = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Anything to add?'),
        content: TextField(controller: ctrl, autofocus: true, maxLines: 3),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, ''), child: const Text('Skip')),
          FilledButton(
              onPressed: () => Navigator.pop(context, ctrl.text), child: const Text('Done')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Journal')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _busy ? null : _addFromPhoto,
        icon: const Icon(Icons.add_a_photo_outlined),
        label: const Text('Photo entry'),
      ),
      body: _entries.isEmpty
          ? const Center(child: Text('Nothing yet. Tap to add a photo entry.'))
          : ListView.builder(
              itemCount: _entries.length,
              itemBuilder: (_, i) {
                final e = _entries[i];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  child: ListTile(
                    title: Text(e['summary'] as String? ?? 'Entry'),
                    subtitle: Text('${e['date']} · mood ${e['mood_score']}'),
                  ),
                );
              },
            ),
    );
  }
}
