import 'dart:convert';
import 'package:flutter/material.dart';
import '../services/gemma_service.dart';
import '../services/storage.dart';
import '../services/notifications.dart';
import 'crisis_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _ctrl = TextEditingController();
  final _scroll = ScrollController();
  final List<_Msg> _msgs = [];
  bool _busy = false;

  Future<void> _send() async {
    final text = _ctrl.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() {
      _msgs.add(_Msg.user(text));
      _busy = true;
      _ctrl.clear();
    });
    try {
      final triage = await GemmaService.instance.triage(text);
      if (triage == null) {
        setState(() => _msgs.add(_Msg.bot('I had trouble understanding. Could you try rewording?')));
        return;
      }
      if (triage['crisis_flag'] == true) {
        if (mounted) {
          Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => CrisisScreen(category: triage['likely_category'] ?? 'other')));
        }
        return;
      }
      setState(() => _msgs.add(_Msg.bot(triage['acknowledgment'] as String? ?? '...')));
      final follow = triage['follow_up_question'];
      if (follow is String && follow.isNotEmpty) {
        setState(() => _msgs.add(_Msg.bot(follow)));
      }

      // Planner pass
      final convo = _msgs.takeLast(8).map((m) => '${m.fromUser ? "USER" : "BOT"}: ${m.text}').join('\n');
      final plan = await GemmaService.instance.plan(triage, convo);
      final calls = (plan?['tool_calls'] as List?) ?? const [];
      for (final c in calls) {
        await _executeToolCall(c as Map<String, dynamic>);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
      _scrollDown();
    }
  }

  Future<void> _executeToolCall(Map<String, dynamic> call) async {
    final name = call['name'];
    final args = (call['arguments'] as Map?)?.cast<String, dynamic>() ?? {};
    switch (name) {
      case 'create_goal_graph':
        await Storage.saveGoalGraph(args);
        setState(() => _msgs.add(_Msg.bot('I sketched a plan for "${args['goal']}". Check the Goals tab.')));
        break;
      case 'save_journal_entry':
        // Always override date with today — the model can hallucinate dates.
        args['date'] = DateTime.now().toIso8601String().substring(0, 10);
        await Storage.saveJournal(args);
        setState(() => _msgs.add(_Msg.bot('Saved today\'s journal entry.')));
        break;
      case 'schedule_reminder':
        final trigger = (args['trigger'] as Map).cast<String, dynamic>();
        final parts = (trigger['time_local'] as String).split(':');
        final notifId = await NotificationsService.scheduleDaily(
          title: args['title'] as String,
          body: args['body'] as String? ?? '',
          hour: int.parse(parts[0]),
          minute: int.parse(parts[1]),
        );
        await Storage.saveReminder(notifId, args);
        setState(() => _msgs.add(_Msg.bot('Reminder set for ${trigger['time_local']} each day.')));
        break;
    }
  }

  void _scrollDown() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Talk')),
      body: Column(children: [
        Expanded(
          child: ListView.builder(
            controller: _scroll,
            padding: const EdgeInsets.all(12),
            itemCount: _msgs.length,
            itemBuilder: (_, i) => _bubble(_msgs[i]),
          ),
        ),
        if (_busy) const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator()),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
            child: Row(children: [
              Expanded(
                child: TextField(
                  controller: _ctrl,
                  decoration: const InputDecoration(
                    hintText: 'How are you feeling?',
                    border: OutlineInputBorder(),
                  ),
                  minLines: 1, maxLines: 4,
                ),
              ),
              IconButton(onPressed: _busy ? null : _send, icon: const Icon(Icons.send)),
            ]),
          ),
        ),
      ]),
    );
  }

  Widget _bubble(_Msg m) {
    final align = m.fromUser ? Alignment.centerRight : Alignment.centerLeft;
    final color = m.fromUser ? Colors.blue.shade100 : Colors.grey.shade200;
    return Align(
      alignment: align,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: const BoxConstraints(maxWidth: 320),
        decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(14)),
        child: Text(m.text),
      ),
    );
  }
}

class _Msg {
  final String text;
  final bool fromUser;
  _Msg.user(this.text) : fromUser = true;
  _Msg.bot(this.text) : fromUser = false;
}

extension _TakeLast<T> on List<T> {
  Iterable<T> takeLast(int n) => skip(length - n.clamp(0, length));
}
