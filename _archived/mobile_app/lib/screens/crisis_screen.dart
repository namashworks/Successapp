import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class CrisisScreen extends StatelessWidget {
  final String category;
  const CrisisScreen({super.key, required this.category});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('You are not alone'), backgroundColor: Colors.red.shade50),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text(
              'What you shared sounds heavy.',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            const Text(
              'A real human can help right now.',
              style: TextStyle(fontSize: 17),
            ),
            const SizedBox(height: 24),
            _hotlineTile('US — 988 Suicide & Crisis Lifeline', '988', 'tel:988'),
            _hotlineTile('UK — Samaritans', '116 123', 'tel:116123'),
            _hotlineTile('India — iCall', '9152987821', 'tel:+919152987821'),
            _hotlineTile('International directory', 'iasp.info', 'https://www.iasp.info/resources/Crisis_Centres/'),
            const SizedBox(height: 24),
            const Text(
              'A few breaths while you decide:',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            const Text('In through your nose for 4. Hold for 4. Out through your mouth for 6. Three times.'),
            const Spacer(),
            OutlinedButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Back to chat'),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _hotlineTile(String label, String number, String urlStr) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.phone_in_talk, color: Colors.redAccent),
        title: Text(label),
        subtitle: Text(number),
        onTap: () => launchUrl(Uri.parse(urlStr)),
      ),
    );
  }
}
