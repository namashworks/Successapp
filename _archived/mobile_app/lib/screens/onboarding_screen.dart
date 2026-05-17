import 'package:flutter/material.dart';
import '../services/storage.dart';
import 'home_screen.dart';

class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 24),
              Text('SuccessApp', style: Theme.of(context).textTheme.headlineLarge),
              const SizedBox(height: 12),
              Text('Your private wellbeing companion.',
                  style: Theme.of(context).textTheme.titleMedium),
              const Spacer(),
              _bullet('100% on-device. Your conversations never leave your phone.'),
              _bullet('Powered by Gemma 4 — Google\'s open AI model.'),
              _bullet('Listens, helps you set goals, and tracks how you feel.'),
              _bullet('If you mention crisis, the app surfaces hotlines immediately.'),
              const Spacer(),
              FilledButton(
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                onPressed: () async {
                  await Storage.setBool('seen_onboarding', true);
                  if (context.mounted) {
                    Navigator.of(context).pushReplacement(
                        MaterialPageRoute(builder: (_) => const HomeScreen()));
                  }
                },
                child: const Text('I understand — continue'),
              ),
              const SizedBox(height: 12),
              const Text(
                'SuccessApp is not a substitute for professional mental-health care.',
                style: TextStyle(fontSize: 12, color: Colors.black54),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _bullet(String t) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('• ', style: TextStyle(fontSize: 18)),
          Expanded(child: Text(t, style: const TextStyle(fontSize: 15))),
        ]),
      );
}
