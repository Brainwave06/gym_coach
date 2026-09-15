import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../core/constants.dart';

class WorkoutStreamEvent {
  final int counter;
  final String stage;
  final List<String> faults;
  final double avgCadence;
  final double fatigueLoss;
  final String? error;

  const WorkoutStreamEvent({
    required this.counter,
    required this.stage,
    required this.faults,
    required this.avgCadence,
    required this.fatigueLoss,
    this.error,
  });

  factory WorkoutStreamEvent.fromJson(Map<String, dynamic> json) {
    return WorkoutStreamEvent(
      counter: (json['counter'] as num?)?.toInt() ?? 0,
      stage: json['stage']?.toString() ?? 'start',
      faults: (json['faults'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      avgCadence: (json['avg_cadence'] as num?)?.toDouble() ?? 2.0,
      fatigueLoss: (json['fatigue_loss'] as num?)?.toDouble() ?? 0.0,
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
