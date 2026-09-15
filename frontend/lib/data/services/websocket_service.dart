import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../core/constants.dart';

class WorkoutStreamEvent {
  final int counter;
  final int goodCounter;
  final String stage;
  final String phase;
  final List<String> faults;
  final double avgCadence;
  final double fatigueLoss;
  final String feedback;
  final bool landmarksDetected;
  final List<Map<String, double>> landmarks;
  final double primaryAngle;
  final double targetDepth;
  final double holdSeconds;
  final double stabilityScore;
  final bool isHold;
  final String? error;

  const WorkoutStreamEvent({
    required this.counter,
    this.goodCounter = 0,
    required this.stage,
    this.phase = 'READY',
    required this.faults,
    required this.avgCadence,
    required this.fatigueLoss,
    this.feedback = '',
    this.landmarksDetected = false,
    this.landmarks = const [],
    this.primaryAngle = 0.0,
    this.targetDepth = 90.0,
    this.holdSeconds = 0.0,
    this.stabilityScore = 100.0,
    this.isHold = false,
    this.error,
  });

  factory WorkoutStreamEvent.fromJson(Map<String, dynamic> json) {
    final rawLms = json['landmarks'] as List<dynamic>? ?? [];
    final parsedLms = <Map<String, double>>[];
    for (final item in rawLms) {
      if (item is Map) {
        parsedLms.add({
          'x': (item['x'] as num?)?.toDouble() ?? 0.0,
          'y': (item['y'] as num?)?.toDouble() ?? 0.0,
          'v': (item['v'] as num?)?.toDouble() ?? 1.0,
        });
      }
    }

    return WorkoutStreamEvent(
      counter: (json['counter'] as num?)?.toInt() ?? 0,
      goodCounter: (json['good_counter'] as num?)?.toInt() ?? (json['counter'] as num?)?.toInt() ?? 0,
      stage: json['stage']?.toString() ?? 'start',
      phase: json['phase']?.toString() ?? (json['stage']?.toString().toUpperCase() ?? 'READY'),
      faults: (json['faults'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      avgCadence: (json['avg_cadence'] as num?)?.toDouble() ?? 2.0,
      fatigueLoss: (json['fatigue_loss'] as num?)?.toDouble() ?? 0.0,
      feedback: json['feedback']?.toString() ?? '',
      landmarksDetected: json['landmarks_detected'] as bool? ?? parsedLms.isNotEmpty,
      landmarks: parsedLms,
      primaryAngle: (json['primary_angle'] as num?)?.toDouble() ?? 0.0,
      targetDepth: (json['target_depth'] as num?)?.toDouble() ?? 90.0,
      holdSeconds: (json['hold_seconds'] as num?)?.toDouble() ?? 0.0,
      stabilityScore: (json['stability_score'] as num?)?.toDouble() ?? 100.0,
      isHold: json['is_hold'] as bool? ?? false,
      error: json['error']?.toString(),
    );
  }
}

class WebSocketService {
  WebSocketChannel? _channel;
  final StreamController<WorkoutStreamEvent> _controller = StreamController<WorkoutStreamEvent>.broadcast();

  Stream<WorkoutStreamEvent> get stream => _controller.stream;
  bool get isConnected => _channel != null;

  void connect(String exerciseId) {
    disconnect();
    final uri = Uri.parse('${AppConstants.wsBaseUrl}/stream/$exerciseId');
    try {
      _channel = WebSocketChannel.connect(uri);
      _channel!.stream.listen(
        (data) {
          try {
            final json = jsonDecode(data.toString()) as Map<String, dynamic>;
            _controller.add(WorkoutStreamEvent.fromJson(json));
          } catch (e) {
            _controller.add(WorkoutStreamEvent(
              counter: 0,
              stage: 'error',
              faults: [],
              avgCadence: 0,
              fatigueLoss: 0,
              error: e.toString(),
            ));
          }
        },
        onError: (err) {
          _controller.add(WorkoutStreamEvent(
            counter: 0,
            stage: 'error',
            faults: [],
            avgCadence: 0,
            fatigueLoss: 0,
            error: 'WebSocket connection error: $err',
          ));
        },
        onDone: () {
          _channel = null;
        },
      );
    } catch (e) {
      _controller.add(WorkoutStreamEvent(
        counter: 0,
        stage: 'error',
        faults: [],
        avgCadence: 0,
        fatigueLoss: 0,
        error: 'Failed to connect: $e',
      ));
    }
  }

  void sendFrameBase64(String base64Jpeg) {
    if (_channel != null) {
      _channel!.sink.add(base64Jpeg);
    }
  }

  void disconnect() {
    _channel?.sink.close();
    _channel = null;
  }

  void dispose() {
    disconnect();
    _controller.close();
  }
}
