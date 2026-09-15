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

    // Rich luxury gradient matching reference (slate indigo to midnight navy)
    final gradient = const LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [
        Color(0xFF4C5D99),
        Color(0xFF283463),
        Color(0xFF131936),
      ],
      stops: [0.0, 0.45, 1.0],
    ).createShader(Rect.fromLTWH(0, 0, w, h));

    final paint = Paint()
      ..shader = gradient
      ..style = PaintingStyle.fill
      ..isAntiAlias = true;

    // 1. Top dynamic wing of 'F' - sweeps right with tapered rounded tip
    final topPath = Path();
    topPath.moveTo(w * 0.36, h * 0.05);
    topPath.cubicTo(w * 0.55, h * 0.02, w * 0.82, h * 0.04, w * 0.96, h * 0.12);
    topPath.cubicTo(w * 1.02, h * 0.16, w * 0.98, h * 0.24, w * 0.90, h * 0.26);
    topPath.cubicTo(w * 0.76, h * 0.28, w * 0.54, h * 0.29, w * 0.32, h * 0.29);
    topPath.cubicTo(w * 0.26, h * 0.20, w * 0.30, h * 0.08, w * 0.36, h * 0.05);
    topPath.close();
    canvas.drawPath(topPath, paint);

    // 2. Middle dynamic crossbar of 'F' - shorter aerodynamic bar
    final midPath = Path();
    midPath.moveTo(w * 0.28, h * 0.38);
    midPath.cubicTo(w * 0.46, h * 0.36, w * 0.68, h * 0.38, w * 0.78, h * 0.44);
    midPath.cubicTo(w * 0.83, h * 0.48, w * 0.80, h * 0.55, w * 0.72, h * 0.56);
    midPath.cubicTo(w * 0.60, h * 0.58, w * 0.42, h * 0.59, w * 0.24, h * 0.59);
    midPath.cubicTo(w * 0.21, h * 0.50, w * 0.24, h * 0.41, w * 0.28, h * 0.38);
    midPath.close();
    canvas.drawPath(midPath, paint);

    // 3. Dynamic slanted vertical stem with rounded foot
    final stemPath = Path();
    stemPath.moveTo(w * 0.38, h * 0.18);
    stemPath.lineTo(w * 0.16, h * 0.88);
    stemPath.cubicTo(w * 0.13, h * 0.97, w * 0.06, h * 1.00, w * 0.02, h * 0.96);
    stemPath.cubicTo(w * -0.01, h * 0.92, w * 0.01, h * 0.84, w * 0.06, h * 0.74);
    stemPath.lineTo(w * 0.24, h * 0.18);
    stemPath.cubicTo(w * 0.28, h * 0.12, w * 0.34, h * 0.13, w * 0.38, h * 0.18);
    stemPath.close();
    canvas.drawPath(stemPath, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
