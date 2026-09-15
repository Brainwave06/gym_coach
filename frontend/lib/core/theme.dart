import 'package:flutter/material.dart';

class AppTheme {
  // Brand Colors - Warm Porcelain & Midnight Navy Aesthetic
  static const Color background = Color(0xFFFAF9F5);
  static const Color backgroundAlt = Color(0xFFF4F0E8);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceWarm = Color(0xFFEFEBE2);
  static const Color surfaceWarmBorder = Color(0xFFE2DCD1);

  static const Color primary = Color(0xFF1B224B);
  static const Color primaryLight = Color(0xFF485482);
  static const Color secondary = Color(0xFF2C3663);
  static const Color accentGold = Color(0xFFC5A880);
  static const Color accentGreen = Color(0xFF10B981);
  static const Color accentCoral = Color(0xFFE53935);

  static const Color textPrimary = Color(0xFF171E3C);
  static const Color textSecondary = Color(0xFF7B8296);
  static const Color textMuted = Color(0xFFA5AAB8);
  static const Color cardBorder = Color(0xFFEDE9E1);

  // Signature Gradients
  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [Color(0xFF45507E), Color(0xFF1B224B)],
  );

  static const LinearGradient warmBackgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFFFAF9F6), Color(0xFFF3EFE9)],
  );

  static List<BoxShadow> get softShadow => [
        BoxShadow(
          color: const Color(0xFF1B224B).withOpacity(0.06),
          blurRadius: 20,
          offset: const Offset(0, 8),
        ),
      ];

  static List<BoxShadow> get buttonShadow => [
        BoxShadow(
          color: const Color(0xFF1B224B).withOpacity(0.25),
          blurRadius: 16,
          offset: const Offset(0, 6),
        ),
      ];

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.light(
        primary: primary,
        secondary: primaryLight,
        surface: surface,
        error: accentCoral,
      ),
      fontFamily: 'Roboto',
      appBarTheme: const AppBarTheme(
        backgroundColor: background,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: textPrimary),
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
        ),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: const BorderSide(color: cardBorder, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(30),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.2,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFFF7F5F0),
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: cardBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: cardBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
        labelStyle: const TextStyle(color: textSecondary),
        hintStyle: TextStyle(color: textSecondary.withOpacity(0.6)),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        elevation: 0,
        indicatorColor: surfaceWarm,
        labelTextStyle: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return const TextStyle(
              color: primary,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            );
          }
          return const TextStyle(color: textSecondary, fontSize: 12);
        }),
        iconTheme: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return const IconThemeData(color: primary, size: 24);
          }
          return const IconThemeData(color: textSecondary, size: 24);
        }),
      ),
    );
  }

  // Preserve darkTheme property as fallback/alias to ensure existing calls resolve cleanly
  static ThemeData get darkTheme => lightTheme;
}
