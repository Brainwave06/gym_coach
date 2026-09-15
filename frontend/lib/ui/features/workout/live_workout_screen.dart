import 'dart:async';
import 'dart:convert';
import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;
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
  bool _isAutoSimulating = false;
  Timer? _autoSimTimer;

  // Camera Controller and Frame Streaming
  List<CameraDescription> _availableCameras = [];
  CameraController? _cameraController;
  int _selectedCameraIndex = 0;
  bool _isCameraInitializing = true;
  bool _isCameraStreaming = false;
  bool _isProcessingFrame = false;
  DateTime _lastFrameSent = DateTime.now();

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

    _initCamera();
    _startSession();
  }

  Future<void> _initCamera() async {
    try {
      _availableCameras = await availableCameras();
      if (_availableCameras.isEmpty) {
        if (mounted) setState(() => _isCameraInitializing = false);
        return;
      }

      // Default to front camera (selfie) for workout tracking so athlete sees form
      int frontIndex = _availableCameras.indexWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
      );
      _selectedCameraIndex = frontIndex != -1 ? frontIndex : 0;
      await _startCamera(_availableCameras[_selectedCameraIndex]);
    } catch (e) {
      if (mounted) {
        setState(() {
          _isCameraInitializing = false;
          _statusError = 'Camera access: $e';
        });
      }
    }
  }

  Future<void> _startCamera(CameraDescription camera) async {
    if (_cameraController != null) {
      try {
        if (_cameraController!.value.isStreamingImages) {
          await _cameraController!.stopImageStream();
        }
      } catch (_) {}
      await _cameraController!.dispose();
      _cameraController = null;
    }

    final controller = CameraController(
      camera,
      ResolutionPreset.medium,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.yuv420,
    );

    _cameraController = controller;

    try {
      await controller.initialize();
      if (!mounted) return;

      _startImageStream(controller);

      setState(() {
        _isCameraInitializing = false;
        _isCameraStreaming = true;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _isCameraInitializing = false;
          _statusError = 'Camera init: $e';
        });
      }
    }
  }

  void _startImageStream(CameraController controller) {
    try {
      controller.startImageStream((CameraImage cameraImage) {
        final now = DateTime.now();
        if (_isProcessingFrame ||
            _isFinished ||
            now.difference(_lastFrameSent).inMilliseconds < 160) {
          return;
        }

        _isProcessingFrame = true;
        _lastFrameSent = now;

        try {
          final jpegBase64 = _convertYuv420ToJpegBase64(cameraImage);
          if (jpegBase64 != null) {
            _wsService.sendFrameBase64(jpegBase64);
          }
        } catch (_) {}

        _isProcessingFrame = false;
      });
    } catch (_) {}
  }

  String? _convertYuv420ToJpegBase64(CameraImage cameraImage) {
    try {
      final width = cameraImage.width;
      final height = cameraImage.height;
      const step = 2; // 2x subsampling for high-speed CV evaluation
      final targetWidth = width ~/ step;
      final targetHeight = height ~/ step;

      final outImage = img.Image(width: targetWidth, height: targetHeight);

      final yPlane = cameraImage.planes[0];
      final uPlane = cameraImage.planes[1];
      final vPlane = cameraImage.planes[2];

      final yBytes = yPlane.bytes;
      final uBytes = uPlane.bytes;
      final vBytes = vPlane.bytes;

      final yRowStride = yPlane.bytesPerRow;
      final uvRowStride = uPlane.bytesPerRow;
      final uvPixelStride = uPlane.bytesPerPixel ?? 1;

      for (int ty = 0; ty < targetHeight; ty++) {
        final srcY = ty * step;
        final yRowOffset = srcY * yRowStride;
        final uvRowOffset = (srcY >> 1) * uvRowStride;

        for (int tx = 0; tx < targetWidth; tx++) {
          final srcX = tx * step;
          final yIdx = yRowOffset + srcX;
          final uvIdx = uvRowOffset + (srcX >> 1) * uvPixelStride;

          if (yIdx >= yBytes.length || uvIdx >= uBytes.length || uvIdx >= vBytes.length) continue;

          final y = yBytes[yIdx];
          final u = uBytes[uvIdx] - 128;
          final v = vBytes[uvIdx] - 128;

          int r = (y + 1.402 * v).round().clamp(0, 255);
          int g = (y - 0.344136 * u - 0.714136 * v).round().clamp(0, 255);
          int b = (y + 1.772 * u).round().clamp(0, 255);

          outImage.setPixelRgb(tx, ty, r, g, b);
        }
      }

      final jpgBytes = img.encodeJpg(outImage, quality: 65);
      return base64Encode(jpgBytes);
    } catch (_) {
      return null;
    }
  }

  Future<void> _switchCamera() async {
    if (_availableCameras.length < 2) return;
    setState(() => _isCameraInitializing = true);
    _selectedCameraIndex = (_selectedCameraIndex + 1) % _availableCameras.length;
    await _startCamera(_availableCameras[_selectedCameraIndex]);
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
    _autoSimTimer?.cancel();
    _subscription?.cancel();
    _wsService.dispose();
    _cameraController?.dispose();
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
    try {
      if (_cameraController != null && _cameraController!.value.isStreamingImages) {
        await _cameraController!.stopImageStream();
      }
    } catch (_) {}

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

  void _simulateSingleRep() {
    if (!mounted) return;
    setState(() {
      _stage = 'ECCENTRIC (DOWN)';
      _activeFaults = [];
    });

    Future.delayed(const Duration(milliseconds: 700), () {
      if (!mounted) return;
      setState(() => _stage = 'INFLECTION (BOTTOM)');

      Future.delayed(const Duration(milliseconds: 600), () {
        if (!mounted) return;
        setState(() => _stage = 'CONCENTRIC (UP)');

        Future.delayed(const Duration(milliseconds: 700), () {
          if (!mounted) return;
          setState(() {
            _reps++;
            _stage = 'READY';
            _avgCadence = 2.0;
            _fatigueLoss = (_fatigueLoss + 3.5).clamp(0.0, 48.0);
          });
          _repPulseController.forward(from: 0.0);
          if (!_isAudioMuted) {
            _soundService.playRepChime();
          }
        });
      });
    });
  }

  void _triggerTestFault() {
    if (!mounted) return;
    setState(() {
      _activeFaults = ['Incomplete Depth', 'Knee Valgus'];
    });
    _faultShakeController.forward(from: 0.0);
    if (!_isAudioMuted) {
      _soundService.playFaultAlert();
    }
    Future.delayed(const Duration(seconds: 4), () {
      if (mounted && _activeFaults.isNotEmpty) {
        setState(() => _activeFaults = []);
      }
    });
  }

  void _toggleAutoSimulation() {
    setState(() {
      _isAutoSimulating = !_isAutoSimulating;
    });
    if (_isAutoSimulating) {
      _simulateSingleRep();
      _autoSimTimer = Timer.periodic(const Duration(milliseconds: 2800), (t) {
        if (!_isAutoSimulating || !mounted) {
          t.cancel();
          return;
        }
        _simulateSingleRep();
      });
    } else {
      _autoSimTimer?.cancel();
      _autoSimTimer = null;
    }
  }
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
          // Camera Switch (Front <-> Back)
          if (_availableCameras.length > 1)
            IconButton(
              icon: const Icon(Icons.flip_camera_ios_rounded, color: Colors.white, size: 20),
              tooltip: 'Switch Camera',
              onPressed: _switchCamera,
            ),
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
                    // 1. Live Camera Preview Feed
                    if (_cameraController != null && _cameraController!.value.isInitialized)
                      SizedBox.expand(
                        child: FittedBox(
                          fit: BoxFit.cover,
                          child: SizedBox(
                            width: _cameraController!.value.previewSize?.height ?? 480,
                            height: _cameraController!.value.previewSize?.width ?? 640,
                            child: CameraPreview(_cameraController!),
                          ),
                        ),
                      )
                    else if (_isCameraInitializing)
                      Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const CircularProgressIndicator(color: AppTheme.accentGold),
                            const SizedBox(height: 16),
                            Text(
                              'Opening Camera Feed...',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.8),
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      )
                    else
                      Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.videocam_off_rounded,
                              size: 80,
                              color: Colors.white.withOpacity(0.5),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              _statusError ?? 'Camera not detected (Use Simulator below)',
                              style: TextStyle(
                                color: _statusError != null ? AppTheme.accentCoral : Colors.white.withOpacity(0.7),
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),

                    // 2. Subtle Dark Gradient Vignette for clear HUD readability
                    Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            Colors.black.withOpacity(0.55),
                            Colors.transparent,
                            Colors.black.withOpacity(0.60),
                          ],
                          stops: const [0.0, 0.4, 1.0],
                        ),
                      ),
                    ),

                    // 3. Pose Tracking Guide Outline when camera is active
                    if (_cameraController != null && _cameraController!.value.isInitialized)
                      Center(
                        child: Opacity(
                          opacity: 0.15,
                          child: Icon(
                            Icons.accessibility_new_rounded,
                            size: 200,
                            color: Colors.white,
                          ),
                        ),
                      ),

                    // 4. Center simulation quick-actions (collapsible / unobtrusive)
                    if (_cameraController == null || !_cameraController!.value.isInitialized)
                      Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const SizedBox(height: 70),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              alignment: WrapAlignment.center,
                              children: [
                                ElevatedButton.icon(
                                  onPressed: _simulateSingleRep,
                                  icon: const Icon(Icons.fitness_center_rounded, size: 16),
                                  label: const Text('Simulate Rep', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.white.withOpacity(0.18),
                                    foregroundColor: Colors.white,
                                    elevation: 0,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(20),
                                      side: BorderSide(color: Colors.white.withOpacity(0.25)),
                                    ),
                                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                  ),
                                ),
                                ElevatedButton.icon(
                                  onPressed: _toggleAutoSimulation,
                                  icon: Icon(_isAutoSimulating ? Icons.pause_circle_rounded : Icons.auto_awesome_rounded, size: 16),
                                  label: Text(
                                    _isAutoSimulating ? 'Stop Auto' : 'Auto Benchmark',
                                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                                  ),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: _isAutoSimulating ? AppTheme.accentGold : Colors.white.withOpacity(0.18),
                                    foregroundColor: _isAutoSimulating ? const Color(0xFF141936) : Colors.white,
                                    elevation: 0,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(20),
                                      side: BorderSide(color: _isAutoSimulating ? AppTheme.accentGold : Colors.white.withOpacity(0.25)),
                                    ),
                                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                  ),
                                ),
                              ],
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
