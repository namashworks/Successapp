import 'package:flutter/material.dart';
import 'chat_screen.dart';
import 'journal_screen.dart';
import 'goals_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;
  final _pages = const [ChatScreen(), GoalsScreen(), JournalScreen()];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.chat_bubble_outline), label: 'Talk'),
          NavigationDestination(icon: Icon(Icons.account_tree_outlined), label: 'Goals'),
          NavigationDestination(icon: Icon(Icons.book_outlined), label: 'Journal'),
        ],
      ),
    );
  }
}
