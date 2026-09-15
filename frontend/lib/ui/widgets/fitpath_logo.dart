import 'package:flutter/material.dart';
import '../../core/theme.dart';

class FitPathLogo extends StatelessWidget {
  final double size;
  final bool showText;
  final TextStyle? textStyle;

  const FitPathLogo({
    super.key,
    this.size = 54,
    this.showText = true,
    this.textStyle,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        CustomPaint(
          size: Size(size, size * 0.9),
          painter: _FitPathLogoPainter(),
        ),
        if (showText) ...[
          const SizedBox(height: 8),
          Text(
            'FitPath',
            style: textStyle ??
                const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.5,
                ),
          ),
        ],
      ],
    );
  }
}

class _FitPathLogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    // Gradient Shader matching reference image (indigo to deep navy)
    final gradient = const LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [
        Color(0xFF5B699E),
        Color(0xFF2C376B),
        Color(0xFF1B224B),
      ],
    ).createShader(Rect.fromLTWH(0, 0, w, h));

    final paint = Paint()
      ..shader = gradient
      ..style = PaintingStyle.fill
      ..isAntiAlias = true;

    // Top dynamic wing / upper stroke of 'F'
    final topPath = Path();
    topPath.moveTo(w * 0.38, 0);
    topPath.cubicTo(w * 0.65, 0, w * 0.95, h * 0.04, w, h * 0.16);
    topPath.cubicTo(w * 0.85, h * 0.28, w * 0.60, h * 0.32, w * 0.34, h * 0.32);
    topPath.lineTo(w * 0.25, h * 0.32);
    topPath.cubicTo(w * 0.22, h * 0.18, w * 0.26, 0, w * 0.38, 0);
    topPath.close();
    canvas.drawPath(topPath, paint);

    // Middle dynamic crossbar of 'F'
    final midPath = Path();
    midPath.moveTo(w * 0.28, h * 0.40);
    midPath.cubicTo(w * 0.50, h * 0.40, w * 0.78, h * 0.42, w * 0.84, h * 0.52);
    midPath.cubicTo(w * 0.70, h * 0.62, w * 0.48, h * 0.64, w * 0.22, h * 0.64);
    midPath.lineTo(w * 0.16, h * 0.64);
    midPath.cubicTo(w * 0.18, h * 0.50, w * 0.22, h * 0.40, w * 0.28, h * 0.40);
    midPath.close();
    canvas.drawPath(midPath, paint);

    // Sleek slanted vertical stem
    final stemPath = Path();
    stemPath.moveTo(w * 0.30, h * 0.26);
    stemPath.lineTo(w * 0.10, h * 0.95);
    stemPath.cubicTo(w * 0.05, h, w * 0.02, h, 0, h * 0.95);
    stemPath.cubicTo(w * 0.02, h * 0.85, w * 0.12, h * 0.45, w * 0.18, h * 0.26);
    stemPath.close();
    canvas.drawPath(stemPath, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
