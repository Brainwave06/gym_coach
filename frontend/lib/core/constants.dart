import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppConstants {
  static const String appName = 'FitPath AI';
  static const String appTagline = 'Your Autonomous AI Fitness Coach';

  // Key for persistent storage
  static const String _prefServerUrlKey = 'fitpath_custom_server_url';

  // Default server URLs:
  // - Live Secure Tunnel URL (works on mobile over 4G/5G/WiFi immediately worldwide):
  static const String defaultTunnelUrl = 'https://5321-2a09-bac5-30cf-2650-00-3d1-2e.ngrok-free.app';
  static const String defaultWifiUrl = 'http://192.168.1.4:8000';
  static const String defaultLocalUrl = 'http://127.0.0.1:8000';

  static final ValueNotifier<String> serverUrlNotifier =
      ValueNotifier<String>(defaultTunnelUrl);

  static Future<void> init() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedUrl = prefs.getString(_prefServerUrlKey);
      if (savedUrl != null && savedUrl.trim().isNotEmpty) {
        serverUrlNotifier.value = savedUrl.trim();
      }
    } catch (_) {}
  }

  static Future<void> setCustomBaseUrl(String url) async {
    var cleaned = url.trim();
    if (cleaned.endsWith('/')) {
      cleaned = cleaned.substring(0, cleaned.length - 1);
    }
    if (!cleaned.startsWith('http://') && !cleaned.startsWith('https://')) {
      cleaned = 'https://$cleaned';
    }
    serverUrlNotifier.value = cleaned;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefServerUrlKey, cleaned);
    } catch (_) {}
  }

  static String get apiBaseUrl {
    final current = serverUrlNotifier.value.trim();
    if (current.isNotEmpty) return current;
    if (kIsWeb) return defaultLocalUrl;
    return defaultTunnelUrl;
  }

  static String get wsBaseUrl {
    final base = apiBaseUrl;
    if (base.startsWith('https://')) {
      return 'wss://${base.substring(8)}';
    } else if (base.startsWith('http://')) {
      return 'ws://${base.substring(7)}';
    }
    return 'ws://127.0.0.1:8000';
  }

  static const List<Map<String, String>> exercises = [
    {'id': 'squat', 'name': 'Barbell/Air Squat', 'category': 'Lower Body', 'icon': 'fitness_center'},
    {'id': 'pushup', 'name': 'Push-up', 'category': 'Chest & Triceps', 'icon': 'accessibility_new'},
    {'id': 'plank', 'name': 'Plank', 'category': 'Core & Stability', 'icon': 'horizontal_rule'},
    {'id': 'rdl', 'name': 'Romanian Deadlift (RDL)', 'category': 'Hamstrings & Glutes', 'icon': 'straighten'},
    {'id': 'overhead_press', 'name': 'Overhead Press (OHP)', 'category': 'Delts & Shoulders', 'icon': 'arrow_upward'},
    {'id': 'lateral_raise', 'name': 'Lateral Raise', 'category': 'Lateral Delts', 'icon': 'compare_arrows'},
    {'id': 'lunge', 'name': 'Walking/Stationary Lunge', 'category': 'Quads & Balance', 'icon': 'directions_walk'},
    {'id': 'biceps_curl', 'name': 'Biceps Curl', 'category': 'Arms', 'icon': 'pan_tool'},
    {'id': 'glute_bridge', 'name': 'Glute Bridge', 'category': 'Posterior Chain', 'icon': 'wb_sunny'},
    {'id': 'wall_sit', 'name': 'Wall Sit', 'category': 'Isometric Quads', 'icon': 'airline_seat_recline_normal'},
  ];
}
