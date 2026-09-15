import 'package:flutter/foundation.dart';

class AppConstants {
  static const String appName = 'FitPath AI';
  static const String appTagline = 'Your Autonomous AI Fitness Coach';

  // Smart API host detection:
  // - Web / Desktop / iOS Simulator: 127.0.0.1
  // - Android Emulator: 10.0.2.2
  static String get apiBaseUrl {
    if (kIsWeb) return 'http://127.0.0.1:8000';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://127.0.0.1:8000';
  }

  static String get wsBaseUrl {
    if (kIsWeb) return 'ws://127.0.0.1:8000';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'ws://10.0.2.2:8000';
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
