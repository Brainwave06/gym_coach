import 'package:flutter/material.dart';
import '../../core/theme.dart';

class SquircleIconCard extends StatelessWidget {
  final IconData icon;
  final double size;
  final double iconSize;
  final Color? backgroundColor;
  final Color? iconColor;
  final VoidCallback? onTap;

  const SquircleIconCard({
    super.key,
    required this.icon,
    this.size = 58,
    this.iconSize = 26,
    this.backgroundColor,
    this.iconColor,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final card = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: backgroundColor ?? AppTheme.surfaceWarm,
        borderRadius: BorderRadius.circular(size * 0.36),
        border: Border.all(
          color: AppTheme.surfaceWarmBorder.withOpacity(0.6),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF1B224B).withOpacity(0.04),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Center(
        child: Icon(
          icon,
          size: iconSize,
          color: iconColor ?? AppTheme.textSecondary,
        ),
      ),
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        child: card,
      );
    }
    return card;
  }
}
