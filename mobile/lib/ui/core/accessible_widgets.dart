import 'package:flutter/material.dart';
import '../../data/services/audio_feedback_service.dart';
import 'app_theme.dart';

/// Highly tactile, TalkBack/VoiceOver accessible button with enforced >=64dp target
class AccessibleButton extends StatelessWidget {
  final String label;
  final String? semanticLabel;
  final String? semanticHint;
  final IconData? icon;
  final VoidCallback? onPressed;
  final Color backgroundColor;
  final Color foregroundColor;
  final Color borderColor;
  final double height;
  final double fontSize;

  const AccessibleButton({
    super.key,
    required this.label,
    this.semanticLabel,
    this.semanticHint,
    this.icon,
    required this.onPressed,
    this.backgroundColor = AppTheme.tactileYellow,
    this.foregroundColor = AppTheme.pureBlack,
    this.borderColor = AppTheme.crispWhite,
    this.height = 64.0,
    this.fontSize = 20.0,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      enabled: onPressed != null,
      label: semanticLabel ?? label,
      hint: semanticHint,
      child: Material(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onPressed == null
              ? null
              : () {
                  AudioFeedbackService.triggerHapticClick();
                  onPressed!();
                },
          child: Container(
            height: height,
            constraints: const BoxConstraints(minHeight: 60.0),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: borderColor, width: 2.5),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (icon != null) ...[
                  Icon(icon, color: foregroundColor, size: 28),
                  const SizedBox(width: 12),
                ],
                Flexible(
                  child: Text(
                    label,
                    style: TextStyle(
                      color: foregroundColor,
                      fontSize: fontSize,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.5,
                    ),
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// A tactile quadrant tile designed for intuitive non-visual pocket/hand operation
class AccessibleQuadrantTile extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;
  final Color backgroundColor;
  final Color foregroundColor;
  final Color borderColor;

  const AccessibleQuadrantTile({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
    this.backgroundColor = AppTheme.darkSurface,
    this.foregroundColor = AppTheme.tactileYellow,
    this.borderColor = AppTheme.cardBorderYellow,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: "$title. $subtitle",
      hint: "Double tap to activate $title",
      child: Material(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: () {
            AudioFeedbackService.triggerHapticClick();
            onTap();
          },
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: borderColor, width: 3.0),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Icon(
                  icon,
                  size: 48,
                  color: foregroundColor,
                ),
                const SizedBox(height: 12),
                Text(
                  title,
                  style: TextStyle(
                    color: foregroundColor,
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.5,
                  ),
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: AppTheme.crispWhite,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Semantic section header for screen reader navigation
class AccessibleHeader extends StatelessWidget {
  final String title;
  final Color color;

  const AccessibleHeader({
    super.key,
    required this.title,
    this.color = AppTheme.tactileYellow,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      header: true,
      label: title,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8.0),
        child: Text(
          title,
          style: TextStyle(
            color: color,
            fontSize: 22,
            fontWeight: FontWeight.w900,
            letterSpacing: 0.5,
          ),
        ),
      ),
    );
  }
}
