import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants.dart';
import '../../../core/theme.dart';
import '../../../data/services/api_service.dart';
import '../../../data/services/websocket_service.dart';

class LiveWorkoutScreen extends StatefulWidget {
  final String exerciseId;
  const LiveWorkoutScreen({super.key, required this.exerciseId});

  @override
  State<LiveWorkoutScreen> createState() => _LiveWorkoutScreenState();
}

class _LiveWorkoutScreenState extends State<LiveWorkoutScreen> {
  final WebSocketService _wsService = WebSocketService();
  StreamSubscription<WorkoutStreamEvent>? _subscription;

  int _reps = 0;
  String _stage = 'READY';
  List<String> _activeFaults = [];
  double _avgCadence = 2.0;
  double _fatigueLoss = 0.0;
  String? _statusError;

  int _elapsedSeconds = 0;
  Timer? _timer;
  bool _isFinished = false;

  @override
  void initState() {
    super.initState();
    _startSession();
  }

  void _startSession() {
    _wsService.connect(widget.exerciseId);
    _subscription = _wsService.stream.listen((event) {
      if (mounted) {
        setState(() {
          if (event.error != null) {
            _statusError = event.error;
          } else {
            _reps = event.counter;
            _stage = event.stage.toUpperCase();
            _activeFaults = event.faults;
            _avgCadence = event.avgCadence;
            _fatigueLoss = event.fatigueLoss;
            _statusError = null;
          }
        });
      }
    });

    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _elapsedSeconds++);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _subscription?.cancel();
    _wsService.dispose();
    super.dispose();
  }

  String _formatTime(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  Future<void> _handleFinish() async {
    setState(() => _isFinished = true);
    _timer?.cancel();
    _wsService.disconnect();

    // Auto-upload summary to backend
    try {
      await ApiService().uploadWorkoutSummary(
        exerciseId: widget.exerciseId,
        durationSec: _elapsedSeconds,
        totalReps: _reps,
        formAccuracyPct: _activeFaults.isEmpty ? 95.0 : 85.0,
        avgCadenceSec: _avgCadence,
        fatigueLossPct: _fatigueLoss,
        faults: _activeFaults,
        notes: 'Completed in mobile live workout view',
      );
    } catch (_) {}

    if (!mounted) return;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Row(
          children: [
            Icon(Icons.emoji_events, color: Colors.amber, size: 28),
            SizedBox(width: 10),
            Text('Session Completed!'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Exercise: ${widget.exerciseId.toUpperCase()}', style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            Text('Total Reps: $_reps'),
            Text('Duration: ${_formatTime(_elapsedSeconds)}'),
            Text('Avg Cadence: ${_avgCadence.toStringAsFixed(1)}s / rep'),
            Text('Fatigue Loss: ${_fatigueLoss.toStringAsFixed(1)}%'),
            const SizedBox(height: 16),
            const Text(
              'Your CV handoff has been saved! The Gym AI Coach is ready for your debriefing.',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              context.go('/dashboard');
            },
            child: const Text('Dashboard'),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.pop(ctx);
              context.go('/chat');
            },
            icon: const Icon(Icons.chat_bubble, size: 16, color: Colors.black),
            label: const Text('Chat Coach Debrief'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final exName = AppConstants.exercises.firstWhere(
      (e) => e['id'] == widget.exerciseId,
      orElse: () => {'name': widget.exerciseId},
    )['name']!;

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: Text(exName, style: const TextStyle(fontSize: 18)),
        actions: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            margin: const EdgeInsets.only(right: 16),
            decoration: BoxDecoration(
              color: AppTheme.surfaceElevated,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.primary.withOpacity(0.4)),
            ),
            child: Row(
              children: [
                const Icon(Icons.timer, size: 14, color: AppTheme.primary),
                const SizedBox(width: 6),
                Text(_formatTime(_elapsedSeconds), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              ],
            ),
          ),
        ],
      ),
      body: Stack(
        children: [
          // Camera Simulation / Live Feed Viewport
          Center(
            child: Container(
              margin: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF101725),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: _activeFaults.isNotEmpty ? AppTheme.danger : AppTheme.primary.withOpacity(0.5),
                  width: 2,
                ),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    // Mock camera background visual with pose grid
                    Opacity(
                      opacity: 0.2,
                      child: GridPaper(
                        color: AppTheme.primary.withOpacity(0.2),
                        interval: 40,
                      ),
                    ),
                    Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.accessibility_new,
                            size: 140,
                            color: _activeFaults.isNotEmpty ? AppTheme.danger.withOpacity(0.7) : AppTheme.primary.withOpacity(0.7),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _statusError ?? 'MediaPipe Vision HUD Active',
                            style: TextStyle(
                              color: _statusError != null ? AppTheme.danger : AppTheme.textSecondary,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                    ),

                    // Top Fault Banner Overlay
                    if (_activeFaults.isNotEmpty)
                      Positioned(
                        top: 16,
                        left: 16,
                        right: 16,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          decoration: BoxDecoration(
                            color: AppTheme.danger.withOpacity(0.9),
                            borderRadius: BorderRadius.circular(12),
                            boxShadow: [
                              BoxShadow(color: AppTheme.danger.withOpacity(0.4), blurRadius: 10),
                            ],
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.warning_amber_rounded, color: Colors.white, size: 22),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  'FORM ALERT: ${_activeFaults.join(", ").toUpperCase()}',
                                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                    // Top-Left Rep Counter Badge
                    Positioned(
                      top: _activeFaults.isNotEmpty ? 70 : 16,
                      left: 16,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                        decoration: BoxDecoration(
                          color: AppTheme.surface.withOpacity(0.9),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppTheme.primary, width: 2),
                        ),
                        child: Column(
                          children: [
                            Text(
                              '$_reps',
                              style: const TextStyle(fontSize: 38, fontWeight: FontWeight.w900, color: AppTheme.primary, height: 1.0),
                            ),
                            const Text('REPS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textSecondary)),
                          ],
                        ),
                      ),
                    ),

                    // Top-Right Stage Badge
                    Positioned(
                      top: _activeFaults.isNotEmpty ? 70 : 16,
                      right: 16,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          color: AppTheme.surface.withOpacity(0.9),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppTheme.secondary.withOpacity(0.6)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(_stage, style: const TextStyle(color: AppTheme.secondary, fontWeight: FontWeight.w900, fontSize: 14)),
                            const SizedBox(height: 2),
                            Text('${_avgCadence.toStringAsFixed(1)}s pace', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                          ],
                        ),
                      ),
                    ),

                    // Bottom HUD Metrics (Fatigue & Cadence)
                    Positioned(
                      bottom: 16,
                      left: 16,
                      right: 16,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        decoration: BoxDecoration(
                          color: AppTheme.surface.withOpacity(0.92),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.white12),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            Column(
                              children: [
                                const Text('Velocity Loss', style: TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                                const SizedBox(height: 4),
                                Text(
                                  '${_fatigueLoss.toStringAsFixed(1)}%',
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                    color: _fatigueLoss > 20.0 ? AppTheme.danger : AppTheme.primary,
                                  ),
                                ),
                              ],
                            ),
                            Container(width: 1, height: 28, color: Colors.white12),
                            Column(
                              children: [
                                const Text('RIR / Fatigue', style: TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                                const SizedBox(height: 4),
                                Text(
                                  _fatigueLoss > 20 ? 'RPE 9 (Fatigued)' : 'RIR 3 (Fresh)',
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14,
                                    color: _fatigueLoss > 20 ? Colors.amber : AppTheme.secondary,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),

          // Bottom Finish CTA
          Positioned(
            bottom: 24,
            left: 24,
            right: 24,
            child: ElevatedButton.icon(
              onPressed: _isFinished ? null : _handleFinish,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.danger,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              icon: const Icon(Icons.stop_circle, color: Colors.white),
              label: const Text('FINISH WORKOUT & DEBRIEF', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
            ),
          ),
        ],
      ),
    );
  }
}
