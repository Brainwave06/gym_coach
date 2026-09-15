import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/constants.dart';
import '../models/app_models.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  static const String _prefAuthTokenKey = 'fitpath_auth_token';
  static const String _prefUserJsonKey = 'fitpath_auth_user';

  String? _authToken;
  User? _currentUser;

  String? get token => _authToken;
  User? get currentUser => _currentUser;
  bool get isAuthenticated => _authToken != null;

  void setAuth(String token, User user) {
    _authToken = token;
    _currentUser = user;
  }

  Future<void> saveAuth(String token, User user) async {
    _authToken = token;
    _currentUser = user;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefAuthTokenKey, token);
      await prefs.setString(_prefUserJsonKey, jsonEncode(user.toJson()));
    } catch (_) {}
  }

  Future<bool> restoreSavedSession() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString(_prefAuthTokenKey);
      final userJson = prefs.getString(_prefUserJsonKey);
      if (token != null && token.isNotEmpty && userJson != null && userJson.isNotEmpty) {
        _authToken = token;
        _currentUser = User.fromJson(jsonDecode(userJson) as Map<String, dynamic>);
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<void> logout() async {
    _authToken = null;
    _currentUser = null;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_prefAuthTokenKey);
      await prefs.remove(_prefUserJsonKey);
    } catch (_) {}
  }

  Map<String, String> _headers({bool isJson = true}) {
    final map = <String, String>{};
    if (isJson) map['Content-Type'] = 'application/json';
    map['ngrok-skip-browser-warning'] = 'true';
    if (_authToken != null) {
      map['Authorization'] = 'Bearer $_authToken';
    }
    return map;
  }

  Future<Map<String, dynamic>> testConnection([String? targetUrl]) async {
    final baseUrl = targetUrl ?? AppConstants.apiBaseUrl;
    final stopwatch = Stopwatch()..start();
    try {
      final uri = Uri.parse(baseUrl);
      final response = await http.get(uri, headers: {
        'ngrok-skip-browser-warning': 'true',
      }).timeout(const Duration(seconds: 4));
      stopwatch.stop();

      if (response.statusCode >= 200 && response.statusCode < 400) {
        return {
          'success': true,
          'latencyMs': stopwatch.elapsedMilliseconds,
          'message': 'Connected (${stopwatch.elapsedMilliseconds}ms)',
        };
      } else {
        return {
          'success': false,
          'latencyMs': stopwatch.elapsedMilliseconds,
          'message': 'Server returned HTTP ${response.statusCode}',
        };
      }
    } catch (e) {
      stopwatch.stop();
      return {
        'success': false,
        'latencyMs': stopwatch.elapsedMilliseconds,
        'message': 'Cannot reach server: $e',
      };
    }
  }

  // ==========================================
  // Auth Services
  // ==========================================

  Future<Map<String, dynamic>> register({
    required String email,
    required String username,
    required String password,
    String? fullName,
  }) async {
    final uri = Uri.parse('${AppConstants.apiBaseUrl}/auth/register');
    final response = await http.post(
      uri,
      headers: _headers(),
      body: jsonEncode({
        'email': email,
        'username': username,
        'password': password,
        'full_name': fullName ?? username,
      }),
    );
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode == 200 && data['status'] == 'success') {
      final token = data['access_token'].toString();
      final user = User.fromJson(data['user'] as Map<String, dynamic>);
      await saveAuth(token, user);
      return {'success': true, 'user': user};
    }
    return {'success': false, 'error': data['detail'] ?? 'Registration failed'};
  }

  Future<Map<String, dynamic>> login({
    required String usernameOrEmail,
    required String password,
  }) async {
    final uri = Uri.parse('${AppConstants.apiBaseUrl}/auth/login');
    final response = await http.post(
      uri,
      headers: _headers(),
      body: jsonEncode({
        'username_or_email': usernameOrEmail,
        'password': password,
      }),
    );
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode == 200 && data['status'] == 'success') {
      final token = data['access_token'].toString();
      final user = User.fromJson(data['user'] as Map<String, dynamic>);
      await saveAuth(token, user);
      return {'success': true, 'user': user};
    }
    return {'success': false, 'error': data['detail'] ?? 'Invalid credentials'};
  }

  Future<Map<String, dynamic>> loginAsDemoAthlete() async {
    try {
      final loginRes = await login(
        usernameOrEmail: 'demo_athlete',
        password: 'demoPassword123',
      );
      if (loginRes['success'] == true) return loginRes;

      final regRes = await register(
        email: 'abdelrahman@fitpath.ai',
        username: 'demo_athlete',
        password: 'demoPassword123',
        fullName: 'Abdelrahman',
      );
      if (regRes['success'] == true) return regRes;
    } catch (_) {}

    // Instant offline fallback demo athlete
    const demoUser = User(
      id: 'usr_demo_athlete',
      email: 'abdelrahman@fitpath.ai',
      username: 'demo_athlete',
      fullName: 'Abdelrahman',
    );
    await saveAuth('demo_jwt_token', demoUser);
    return {'success': true, 'user': demoUser};
  }

  // ==========================================
  // Profile & Biometrics Services
  // ==========================================

  Future<AthleteProfile?> getProfile() async {
    try {
      final uri = Uri.parse('${AppConstants.apiBaseUrl}/profile');
      final response = await http.get(uri, headers: _headers());
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final rawProf = data['profile'] as Map<String, dynamic>? ?? {};
        final rawBio = data['biometrics'] as Map<String, dynamic>? ?? {};
        final biometrics = Biometrics.fromJson(rawBio);
        return AthleteProfile.fromJson(rawProf, biometrics: biometrics);
      }
    } catch (_) {}
    return null;
  }

  Future<AthleteProfile?> updateProfile(Map<String, dynamic> updates) async {
    try {
      final uri = Uri.parse('${AppConstants.apiBaseUrl}/profile');
      final response = await http.put(
        uri,
        headers: _headers(),
        body: jsonEncode(updates),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final rawProf = data['profile'] as Map<String, dynamic>? ?? {};
        final rawBio = data['biometrics'] as Map<String, dynamic>? ?? {};
        final biometrics = Biometrics.fromJson(rawBio);
        return AthleteProfile.fromJson(rawProf, biometrics: biometrics);
      }
    } catch (_) {}
    return null;
  }

  // ==========================================
  // Workout Plan & Chat Services
  // ==========================================

  Future<Map<String, dynamic>> getWorkoutPlan() async {
    try {
      final uri = Uri.parse('${AppConstants.apiBaseUrl}/plan');
      final response = await http.get(uri, headers: _headers());
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return {'status': 'default', 'plan': []};
  }

  Future<Map<String, dynamic>> generatePlan() async {
    final uri = Uri.parse('${AppConstants.apiBaseUrl}/chatbot/generate_plan');
    final response = await http.post(uri, headers: _headers(), body: jsonEncode({}));
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to generate plan');
  }

  Future<String> sendChatMessage(String query, {List<Map<String, dynamic>>? history}) async {
    final uri = Uri.parse('${AppConstants.apiBaseUrl}/chat');
    final response = await http.post(
      uri,
      headers: _headers(),
      body: jsonEncode({
        'query': query,
        'chat_history': history ?? [],
        'include_profile': true,
      }),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['answer']?.toString() ?? 'No response received.';
    }
    return 'Coach connection error (${response.statusCode}). Please try again.';
  }

  Future<String> getPostWorkoutDebrief() async {
    final uri = Uri.parse('${AppConstants.apiBaseUrl}/chat/debrief');
    final response = await http.get(uri, headers: _headers());
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['debrief']?.toString() ?? 'Great workout!';
    }
    return 'Workout completed! Keep up the great consistency.';
  }

  // ==========================================
  // Plate Vision Food Analyzer Service
  // ==========================================

  Future<MealAnalysis?> analyzeMeal({
    required Uint8List imageBytes,
    required String filename,
    String notes = '',
  }) async {
    final uri = Uri.parse('${AppConstants.apiBaseUrl}/chat/vision-meal');
    final request = http.MultipartRequest('POST', uri);
    if (_authToken != null) {
      request.headers['Authorization'] = 'Bearer $_authToken';
    }

    String mimeType = 'image/jpeg';
    if (filename.toLowerCase().endsWith('.png')) mimeType = 'image/png';
    if (filename.toLowerCase().endsWith('.webp')) mimeType = 'image/webp';

    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        imageBytes,
        filename: filename,
        contentType: MediaType.parse(mimeType),
      ),
    );
    if (notes.isNotEmpty) {
      request.fields['notes'] = notes;
    }

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final mealData = data['meal'] as Map<String, dynamic>?;
      if (mealData != null) {
        return MealAnalysis.fromJson(mealData);
      }
    }
    throw Exception('Vision analysis failed (${response.statusCode}): ${response.body}');
  }

  // ==========================================
  // Workout Summary & Session Upload Service
  // ==========================================

  Future<Map<String, dynamic>> uploadWorkoutSummary({
    required String exerciseId,
    required int durationSec,
    required int totalReps,
    double formAccuracyPct = 100.0,
    double avgCadenceSec = 2.0,
    double fatigueLossPct = 0.0,
    List<String>? faults,
    double weightKg = 0.0,
    String notes = '',
  }) async {
    final uri = Uri.parse('${AppConstants.apiBaseUrl}/workout/summary');
    final response = await http.post(
      uri,
      headers: _headers(),
      body: jsonEncode({
        'user_id': _currentUser?.id ?? 'default',
        'exercise_id': exerciseId,
        'duration_sec': durationSec,
        'total_reps': totalReps,
        'form_accuracy_pct': formAccuracyPct,
        'avg_cadence_sec': avgCadenceSec,
        'fatigue_velocity_loss_pct': fatigueLossPct,
        'faults': faults ?? [],
        'weight_kg': weightKg,
        'notes': notes,
      }),
    );
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
