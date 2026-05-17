import 'package:flutter/material.dart';
import 'services/gemma_service.dart';
import 'services/storage.dart';
import 'services/notifications.dart';
import 'screens/onboarding_screen.dart';
import 'screens/home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Storage.init();
  await NotificationsService.init();
  await GemmaService.instance.loadModel();
  runApp(const SuccessApp());
}

class SuccessApp extends StatelessWidget {
  const SuccessApp({super.key});

  @override
  Widget build(BuildContext context) {
    final seenOnboarding = Storage.getBool('seen_onboarding') ?? false;
    return MaterialApp(
      title: 'SuccessApp',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4A6FA5)),
        useMaterial3: true,
      ),
      home: seenOnboarding ? const HomeScreen() : const OnboardingScreen(),
    );
  }
}
