import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

class NotificationsService {
  static final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  static Future<void> init() async {
    tz.initializeTimeZones();
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const init = InitializationSettings(android: android);
    await _plugin.initialize(init);
  }

  /// Schedules a daily reminder. Returns the platform notification id.
  static Future<int> scheduleDaily(
      {required String title, required String body, required int hour, required int minute}) async {
    final id = DateTime.now().millisecondsSinceEpoch.remainder(1 << 31);
    final now = tz.TZDateTime.now(tz.local);
    var when = tz.TZDateTime(tz.local, now.year, now.month, now.day, hour, minute);
    if (when.isBefore(now)) when = when.add(const Duration(days: 1));
    await _plugin.zonedSchedule(
      id, title, body, when,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'successapp_reminders', 'Reminders',
          channelDescription: 'Daily nudges from SuccessApp',
          importance: Importance.high, priority: Priority.high,
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      matchDateTimeComponents: DateTimeComponents.time,
    );
    return id;
  }
}
