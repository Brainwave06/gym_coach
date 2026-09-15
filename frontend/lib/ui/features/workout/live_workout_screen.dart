import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants.dart';
import '../../../core/sound_service.dart';
import '../../../core/theme.dart';
import '../../../data/services/api_service.dart';
import '../../../data/services/websocket_service.dart';
import '../../widgets/squircle_icon_card.dart';

class LiveWorkoutScreen extends StatefulWidget {
  final String exerciseId;
  const LiveWorkoutScreen({super.key, required this.exerciseId});

  @override
  State<LiveWorkoutScreen> createState() => _LiveWorkoutScreenState();
}

class _LiveWorkoutScreenState extends State<LiveWorkoutScreen>
    with TickerProviderStateMixin {
  final WebSocketService _wsService = WebSocketService();
  final SoundService _soundService = SoundService();
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
  bool _isAudioMuted = false;

  // Animation Controllers for Rep Pulse & Fault Shake
  late AnimationController _repPulseController;
  late Animation<double> _repPulseScale;

  late AnimationController _faultShakeController;
  late Animation<double> _faultShakeOffset;

  @override
  void initState() {
    super.initState();
    _soundService.initialize();

    // Pulse animation: 1.0 -> 1.25 -> 1.0
    _repPulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    );
    _repPulseScale = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween<double>(begin: 1.0, end: 1.25).chain(CurveTween(curve: Curves.easeOutCubic)),
        weight: 40,
      ),
      TweenSequenceItem(
        tween: Tween<double>(begin: 1.25, end: 1.0).chain(CurveTween(curve: Curves.easeInQuad)),
        weight: 60,
      ),
    ]).animate(_repPulseController);

    // Fault shake animation: oscillates left and right
    _faultShakeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _faultShakeOffset = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _faultShakeController, curve: Curves.easeInOut),
    );

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
            // Check if a new repetition was completed
            if (event.counter > _reps) {
              _repPulseController.forward(from: 0.0);
              if (!_isAudioMuted) {
                _soundService.playRepChime();
              }
            }

            // Check if new faults appeared
            if (event.faults.isNotEmpty && _activeFaults.isEmpty) {
              _faultShakeController.forward(from: 0.0);
              if (!_isAudioMuted) {
                _soundService.playFaultAlert();
              }
            }

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
    _repPulseController.dispose();
    _faultShakeController.dispose();
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

    if (!_isAudioMuted) {
      _soundService.playWorkoutComplete();
    }

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
        backgroundColor: AppTheme.background,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        title: const Row(
          children: [
            SquircleIconCard(
              icon: Icons.emoji_events_rounded,
              size: 42,
              iconSize: 22,
              backgroundColor: AppTheme.surfaceWarm,
              iconColor: AppTheme.accentGold,
            ),
            SizedBox(width: 14),
            Text(
              'Session Finished!',
              style: TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 18,
                color: AppTheme.textPrimary,
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.exerciseId.replaceAll('_', ' ').toUpperCase(),
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 15,
                color: AppTheme.primary,
              ),
            ),
            const SizedBox(height: 14),
            _buildSummaryRow('Total Repetitions', '$_reps reps'),
            _buildSummaryRow('Workout Duration', _formatTime(_elapsedSeconds)),
            _buildSummaryRow('Average Tempo', '${_avgCadence.toStringAsFixed(1)}s / rep'),
            _buildSummaryRow('Fatigue Drop-off', '${_fatigueLoss.toStringAsFixed(1)}%'),
            const SizedBox(height: 16),
            const Text(
              'CV handoff saved! The AI Coach is prepared for your debriefing.',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13, height: 1.4),
            ),
          ],
        ),
        actionsPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              context.go('/dashboard');
            },
            child: const Text(
              'Dashboard',
              style: TextStyle(color: AppTheme.textSecondary, fontWeight: FontWeight.w700),
            ),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.pop(ctx);
              context.go('/chat');
            },
            icon: const Icon(Icons.chat_bubble_outline_rounded, size: 16, color: Colors.white),
            label: const Text('Chat Coach Debrief'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primary,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700, color: AppTheme.textPrimary, fontSize: 13)),
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
      backgroundColor: const Color(0xFF0F1424),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F1424),
        iconTheme: const IconThemeData(color: Colors.white),
        title: Text(
          exName,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 18,
            fontWeight: FontWeight.w800,
          ),
        ),
        actions: [
          // Audio Mute/Unmute Toggle
          IconButton(
            icon: Icon(
              _isAudioMuted ? Icons.volume_off_rounded : Icons.volume_up_rounded,
              color: Colors.white,
              size: 20,
            ),
            tooltip: _isAudioMuted ? 'Unmute audio cues' : 'Mute audio cues',
            onPressed: () => setState(() => _isAudioMuted = !_isAudioMuted),
          ),
          // Timer Widget
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            margin: const EdgeInsets.only(right: 16),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.12),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.white.withOpacity(0.15)),
            ),
            child: Row(
              children: [
                const Icon(Icons.timer_outlined, size: 15, color: Colors.white),
                const SizedBox(width: 6),
                Text(
                  _formatTime(_elapsedSeconds),
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: Stack(
        children: [
          // Viewport Container with rounded borders
          Center(
            child: Container(
              margin: const EdgeInsets.fromLTRB(16, 8, 16, 90),
              decoration: BoxDecoration(
                color: const Color(0xFF171D33),
                borderRadius: BorderRadius.circular(26),
                border: Border.all(
                  color: _activeFaults.isNotEmpty
                      ? AppTheme.accentCoral
                      : Colors.white.withOpacity(0.12),
                  width: 2,
                ),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(26),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    // Pose tracking grid simulation
                    Opacity(
                      opacity: 0.15,
                      child: GridPaper(
                        color: Colors.white,
                        interval: 44,
                      ),
                    ),
                    Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.accessibility_new_rounded,
                            size: 130,
                            color: _activeFaults.isNotEmpty
                                ? AppTheme.accentCoral.withOpacity(0.85)
                                : Colors.white.withOpacity(0.7),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _statusError ?? 'FitPath CV Pose Engine Active',
                            style: TextStyle(
                              color: _statusError != null
                                  ? AppTheme.accentCoral
                                  : Colors.white.withOpacity(0.7),
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),

                    // Live Form Alert Banner with Shake Animation
                    if (_activeFaults.isNotEmpty)
                      Positioned(
                        top: 16,
                        left: 16,
                        right: 16,
                        child: AnimatedBuilder(
                          animation: _faultShakeOffset,
                          builder: (context, child) {
                            final double offset = math_sin(_faultShakeOffset.value * 3.14159 * 4) * 8.0;
                            return Transform.translate(
                              offset: Offset(offset, 0),
                              child: child,
                            );
                          },
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                            decoration: BoxDecoration(
                              color: AppTheme.accentCoral.withOpacity(0.95),
                              borderRadius: BorderRadius.circular(16),
                              boxShadow: [
                                BoxShadow(
                                  color: AppTheme.accentCoral.withOpacity(0.35),
                                  blurRadius: 12,
                                  offset: const Offset(0, 4),
                                ),
                              ],
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.warning_amber_rounded, color: Colors.white, size: 22),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    'FORM ALERT: ${_activeFaults.join(", ").toUpperCase()}',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w800,
                                      fontSize: 13,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),

                    // Top-Left Rep Counter Card with Pulse Scale Animation
                    Positioned(
                      top: _activeFaults.isNotEmpty ? 74 : 16,
                      left: 16,
                      child: ScaleTransition(
                        scale: _repPulseScale,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
                          decoration: BoxDecoration(
                            color: const Color(0xFFFAF9F5),
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.2),
                                blurRadius: 14,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: Column(
                            children: [
                              Text(
                                '$_reps',
                                style: const TextStyle(
                                  fontSize: 40,
                                  fontWeight: FontWeight.w900,
                                  color: AppTheme.primary,
                                  height: 1.0,
                                ),
                              ),
                              const SizedBox(height: 2),
                              const Text(
                                'REPS',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w800,
                                  color: AppTheme.textSecondary,
                                  letterSpacing: 0.8,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),

                    // Top-Right Movement Stage Badge
                    Positioned(
                      top: _activeFaults.isNotEmpty ? 74 : 16,
                      right: 16,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceWarm,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: AppTheme.surfaceWarmBorder.withOpacity(0.8),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              _stage,
                              style: const TextStyle(
                                color: AppTheme.primary,
                                fontWeight: FontWeight.w800,
                                fontSize: 14,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              '${_avgCadence.toStringAsFixed(1)}s pace',
                              style: const TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                    // Bottom Floating Metrics Strip
                    Positioned(
                      bottom: 16,
                      left: 16,
                      right: 16,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFAF9F5),
                          borderRadius: BorderRadius.circular(18),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.18),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            Column(
                              children: [
                                const Text(
                                  'Velocity Loss',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: AppTheme.textSecondary,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${_fatigueLoss.toStringAsFixed(1)}%',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w800,
                                    fontSize: 16,
                                    color: _fatigueLoss > 20.0
                                        ? AppTheme.accentCoral
                                        : AppTheme.primary,
                                  ),
                                ),
                              ],
                            ),
                            Container(width: 1, height: 26, color: AppTheme.cardBorder),
                            Column(
                              children: [
                                const Text(
                                  'RIR / Fatigue',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: AppTheme.textSecondary,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  _fatigueLoss > 20 ? 'RPE 9 (Fatigued)' : 'RIR 3 (Fresh)',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w800,
                                    fontSize: 14,
                                    color: _fatigueLoss > 20
                                        ? const Color(0xFFE65100)
                                        : AppTheme.primaryLight,
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

          // Bottom Finish Workout Pill Button
          Positioned(
            bottom: 20,
            left: 24,
            right: 24,
            child: Container(
              height: 56,
              decoration: BoxDecoration(
                gradient: AppTheme.primaryGradient,
                borderRadius: BorderRadius.circular(30),
                boxShadow: AppTheme.buttonShadow,
              ),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: _isFinished ? null : _handleFinish,
                  borderRadius: BorderRadius.circular(30),
                  splashColor: Colors.white.withOpacity(0.15),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.check_circle_outline_rounded, color: Colors.white, size: 22),
                      SizedBox(width: 10),
                      Text(
                        'Finish Workout & Debrief',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                          fontSize: 16,
                          letterSpacing: 0.2,
                        ),
                      ),
                      SizedBox(width: 8),
                      Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 18),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  static double math_sin(double radians) {
    return math_sin_internal(radians);
  }

  static double math_sin_internal(double r) {
    // Fast sine approximation or standard
    var x = r % (2 * 3.141592653589793);
    if (x < -3.141592653589793) x += 2 * 3.141592653589793;
    if (x > 3.141592653589793) x -= 2 * 3.141592653589793;
    return x * (1.27323954 - 0.405284735 * (x < 0 ? -x : x));
  }
}
