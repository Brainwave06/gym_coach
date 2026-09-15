import 'package:flutter/material.dart';

class SkeletonOverlayPainter extends CustomPainter {
  final List<Map<String, double>> landmarks;
  final bool isFaultActive;
  final bool isFrontCamera;

  const SkeletonOverlayPainter({
    required this.landmarks,
    required this.isFaultActive,
    this.isFrontCamera = true,
  });

  // Standard MediaPipe Pose 33 connections
  static const List<List<int>> connections = [
    // Torso box
    [11, 12], [11, 23], [12, 24], [23, 24],
    // Left Arm
    [11, 13], [13, 15],
    // Right Arm
    [12, 14], [14, 16],
    // Left Leg
    [23, 25], [25, 27], [27, 29], [27, 31],
    // Right Leg
    [24, 26], [26, 28], [28, 30], [28, 32],
    // Head cues
    [7, 0], [0, 8],
  ];

  @override
  void paint(Canvas canvas, Size size) {
    if (landmarks.length < 33) return;

    final baseColor = isFaultActive ? const Color(0xFFEF4444) : const Color(0xFF10B981);
    final glowColor = isFaultActive ? const Color(0x66EF4444) : const Color(0x6610B981);

    // Bone Glow Paint
    final glowPaint = Paint()
      ..color = glowColor
      ..strokeWidth = 7.0
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    // Bone Core Paint
    final linePaint = Paint()
      ..color = baseColor
      ..strokeWidth = 3.5
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    // Joint Outer Paint
    final jointOuterPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.fill;

    // Joint Inner Paint
    final jointInnerPaint = Paint()
      ..color = baseColor
      ..style = PaintingStyle.fill;

    Offset? getOffset(int index) {
      if (index >= landmarks.length) return null;
      final lm = landmarks[index];
      final v = lm['v'] ?? 1.0;
      if (v < 0.35) return null; // Low confidence threshold

      double x = lm['x'] ?? 0.0;
      double y = lm['y'] ?? 0.0;

      // Selfie / front-camera mirror adjustment
      if (isFrontCamera) {
        x = 1.0 - x;
      }

      return Offset(x * size.width, y * size.height);
    }

    // Draw Bone Connections
    for (final pair in connections) {
      final p1 = getOffset(pair[0]);
      final p2 = getOffset(pair[1]);
      if (p1 != null && p2 != null) {
        canvas.drawLine(p1, p2, glowPaint);
        canvas.drawLine(p1, p2, linePaint);
      }
    }

    // Draw Major Joint Keypoints
    const majorJoints = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28];
    for (final idx in majorJoints) {
      final pos = getOffset(idx);
      if (pos != null) {
        canvas.drawCircle(pos, 5.0, jointOuterPaint);
        canvas.drawCircle(pos, 3.0, jointInnerPaint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant SkeletonOverlayPainter oldDelegate) {
    return oldDelegate.landmarks != landmarks ||
        oldDelegate.isFaultActive != isFaultActive ||
        oldDelegate.isFrontCamera != isFrontCamera;
  }
}
