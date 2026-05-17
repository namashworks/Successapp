import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

/// All persistence is local. Zero network calls. The user's data never leaves the device.
class Storage {
  static late SharedPreferences _prefs;
  static late Database _db;

  static Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    final dir = await getApplicationDocumentsDirectory();
    final path = p.join(dir.path, 'successapp.db');
    _db = await openDatabase(
      path,
      version: 1,
      onCreate: (db, v) async {
        await db.execute('''
          CREATE TABLE journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            mood_score INTEGER,
            payload TEXT NOT NULL
          )
        ''');
        await db.execute('''
          CREATE TABLE goal_graphs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            goal TEXT NOT NULL,
            payload TEXT NOT NULL
          )
        ''');
        await db.execute('''
          CREATE TABLE reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_id INTEGER UNIQUE,
            title TEXT NOT NULL,
            body TEXT,
            payload TEXT NOT NULL
          )
        ''');
      },
    );
  }

  static SharedPreferences get prefs => _prefs;
  static Database get db => _db;

  static bool? getBool(String k) => _prefs.getBool(k);
  static Future<bool> setBool(String k, bool v) => _prefs.setBool(k, v);

  static Future<int> saveJournal(Map<String, dynamic> entry) =>
      _db.insert('journal_entries', {
        'date': entry['date'],
        'mood_score': entry['mood_score'],
        'payload': jsonEncode(entry),
      });

  static Future<List<Map<String, dynamic>>> listJournal() async {
    final rows = await _db.query('journal_entries', orderBy: 'date DESC', limit: 90);
    return rows.map((r) => jsonDecode(r['payload'] as String) as Map<String, dynamic>).toList();
  }

  static Future<int> saveGoalGraph(Map<String, dynamic> g) =>
      _db.insert('goal_graphs', {
        'created_at': DateTime.now().toIso8601String(),
        'goal': g['goal'],
        'payload': jsonEncode(g),
      });

  static Future<List<Map<String, dynamic>>> listGoalGraphs() async {
    final rows = await _db.query('goal_graphs', orderBy: 'created_at DESC');
    return rows.map((r) => jsonDecode(r['payload'] as String) as Map<String, dynamic>).toList();
  }

  static Future<int> saveReminder(int notifId, Map<String, dynamic> r) =>
      _db.insert('reminders', {
        'notification_id': notifId,
        'title': r['title'],
        'body': r['body'],
        'payload': jsonEncode(r),
      });
}
