import 'package:flutter/material.dart';

/// VisionAid Accessible High-Contrast Theme System
///
/// Designed in accordance with WCAG AAA accessibility guidelines for low-vision
/// and visually impaired users. Employs deep OLED blacks and intense tactile yellow
/// for maximum optical contrast (>15:1 ratio), bold typography, and minimum 60dp
/// interactive target sizing.
class AppTheme {
  // ── High Contrast Color Palette (WCAG AAA Compliant) ──────────────────────
  static const Color pureBlack = Color(0xFF000000);
  static const Color tactileYellow = Color(0xFFFFD700);
  static const Color crispWhite = Color(0xFFFFFFFF);
  static const Color darkSurface = Color(0xFF161616);
  static const Color cardBorderYellow = Color(0xFFFFD700);
  
  // Status Indicator Colors
  static const Color statusGreen = Color(0xFF00E676);
  static const Color statusRed = Color(0xFFFF1744);
  static const Color statusAmber = Color(0xFFFF9100);

  // ── High Contrast Dark Theme ──────────────────────────────────────────────
  static ThemeData get highContrastTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: pureBlack,
      primaryColor: tactileYellow,
      colorScheme: const ColorScheme.dark(
        primary: tactileYellow,
        onPrimary: pureBlack,
        secondary: crispWhite,
        onSecondary: pureBlack,
        surface: darkSurface,
        onSurface: crispWhite,
        error: statusRed,
        onError: crispWhite,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: pureBlack,
        foregroundColor: tactileYellow,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: TextStyle(
          color: tactileYellow,
          fontSize: 22,
          fontWeight: FontWeight.w900,
          letterSpacing: 0.5,
        ),
        iconTheme: IconThemeData(color: tactileYellow, size: 28),
      ),
      cardTheme: CardTheme(
        color: darkSurface,
        elevation: 4,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: tactileYellow, width: 2.5),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: tactileYellow,
          foregroundColor: pureBlack,
          minimumSize: const Size.fromHeight(64),
          elevation: 4,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: crispWhite, width: 2.0),
          ),
          textStyle: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w900,
            letterSpacing: 0.5,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: tactileYellow,
          minimumSize: const Size.fromHeight(60),
          side: const BorderSide(color: tactileYellow, width: 2.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      sliderTheme: const SliderThemeData(
        activeTrackColor: tactileYellow,
        inactiveTrackColor: Color(0xFF444444),
        thumbColor: tactileYellow,
        overlayColor: Color(0x33FFD700),
        thumbShape: RoundSliderThumbShape(enabledThumbRadius: 16.0),
        trackHeight: 8.0,
      ),
      switchTheme: SwitchThemeData(
        thumbColor: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return tactileYellow;
          }
          return Colors.grey;
        }),
        trackColor: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return const Color(0xFF665500);
          }
          return const Color(0xFF333333);
        }),
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(
          color: tactileYellow,
          fontSize: 28,
          fontWeight: FontWeight.w900,
        ),
        headlineMedium: TextStyle(
          color: crispWhite,
          fontSize: 24,
          fontWeight: FontWeight.bold,
        ),
        titleLarge: TextStyle(
          color: tactileYellow,
          fontSize: 20,
          fontWeight: FontWeight.w800,
        ),
        titleMedium: TextStyle(
          color: crispWhite,
          fontSize: 18,
          fontWeight: FontWeight.w700,
        ),
        bodyLarge: TextStyle(
          color: crispWhite,
          fontSize: 18,
          fontWeight: FontWeight.w600,
          height: 1.4,
        ),
        bodyMedium: TextStyle(
          color: Color(0xFFCCCCCC),
          fontSize: 16,
          fontWeight: FontWeight.w500,
          height: 1.3,
        ),
      ),
    );
  }

  // ── Standard Dark Theme (Softened for users with mild visual impairment) ──
  static ThemeData get standardDarkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: const Color(0xFF121212),
      primaryColor: const Color(0xFF42A5F5),
      colorScheme: const ColorScheme.dark(
        primary: Color(0xFF42A5F5),
        surface: Color(0xFF1E1E1E),
        onSurface: Colors.white,
      ),
    );
  }
}
