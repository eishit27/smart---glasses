import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../data/models/glasses_status.dart';
import '../../core/app_theme.dart';
import '../../core/accessible_widgets.dart';
import 'home_view_model.dart';
import '../faces/face_enrollment_view.dart';
import '../settings/settings_view.dart';

/// Primary accessible 4-quadrant tactile dashboard for VisionAid
class HomeView extends StatelessWidget {
  const HomeView({super.key});

  @override
  Widget build(BuildContext context) {
    final viewModel = context.watch<HomeViewModel>();
    final status = viewModel.status;

    return Scaffold(
      backgroundColor: AppTheme.pureBlack,
      appBar: AppBar(
        title: const Text(
          "VISIONAID",
          style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 2.0),
        ),
        actions: [
          IconButton(
            tooltip: "Settings and Safety Controls",
            icon: const Icon(Icons.settings, size: 30),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const SettingsView()),
              );
            },
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
          child: Column(
            children: [
              // ── Top Connection & Battery Status Card ────────────────────────
              _buildStatusBar(context, viewModel, status),
              const SizedBox(height: 12),

              // ── Main 4-Quadrant Tactile Navigation Grid ─────────────────────
              Expanded(
                child: _buildTactileQuadrants(context, viewModel),
              ),
              const SizedBox(height: 12),

              // ── Real-Time Spoken Alert Display Bar ──────────────────────────
              _buildSpokenAlertBar(status),
              const SizedBox(height: 12),

              // ── Quick Face Enrollment Navigation Button ─────────────────────
              AccessibleButton(
                label: "MANAGE KNOWN FACES",
                semanticLabel: "Manage Known Faces. View family and friends enrolled for face recognition.",
                icon: Icons.people_alt_rounded,
                height: 58,
                backgroundColor: AppTheme.darkSurface,
                foregroundColor: AppTheme.tactileYellow,
                borderColor: AppTheme.tactileYellow,
                fontSize: 18,
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const FaceEnrollmentView()),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusBar(
    BuildContext context,
    HomeViewModel viewModel,
    GlassesStatus status,
  ) {
    Color indicatorColor;
    String statusText;

    switch (status.state) {
      case ConnectionState.connected:
        indicatorColor = AppTheme.statusGreen;
        statusText = "GLASSES CONNECTED";
        break;
      case ConnectionState.connecting:
      case ConnectionState.scanning:
      case ConnectionState.authenticating:
        indicatorColor = AppTheme.statusAmber;
        statusText = "CONNECTING...";
        break;
      case ConnectionState.disconnected:
      case ConnectionState.error:
      default:
        indicatorColor = AppTheme.statusRed;
        statusText = "DISCONNECTED (TAP TO PAIR)";
        break;
    }

    return Semantics(
      button: true,
      label: viewModel.connectionStatusAnnouncement,
      hint: "Double tap to change connection state",
      child: Material(
        color: AppTheme.darkSurface,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () {
            if (status.isConnected) {
              viewModel.disconnect();
            } else {
              viewModel.connect("visionaid-secure-pair-token");
            }
          },
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: indicatorColor, width: 2.5),
            ),
            child: Row(
              children: [
                Container(
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(
                    color: indicatorColor,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        statusText,
                        style: TextStyle(
                          color: indicatorColor,
                          fontSize: 16,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      Text(
                        status.isConnected
                            ? "Battery: ${status.batteryPercent}%  •  ${status.currentMode.name.toUpperCase()} MODE"
                            : "Glasses offline • Tap to reconnect",
                        style: const TextStyle(
                          color: AppTheme.crispWhite,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  status.isConnected ? Icons.battery_charging_full_rounded : Icons.bluetooth_searching,
                  color: indicatorColor,
                  size: 28,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTactileQuadrants(BuildContext context, HomeViewModel viewModel) {
    return Column(
      children: [
        // Upper Two Quadrants
        Expanded(
          child: Row(
            children: [
              Expanded(
                child: AccessibleQuadrantTile(
                  title: "DESCRIBE",
                  subtitle: "Scan Surroundings",
                  icon: Icons.visibility_rounded,
                  onTap: () => viewModel.scanScene(),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: AccessibleQuadrantTile(
                  title: "READ TEXT",
                  subtitle: "Signs, Menus, OCR",
                  icon: Icons.document_scanner_rounded,
                  onTap: () => viewModel.readText(),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        // Lower Two Quadrants
        Expanded(
          child: Row(
            children: [
              Expanded(
                child: AccessibleQuadrantTile(
                  title: "WHO IS HERE?",
                  subtitle: "Identify People",
                  icon: Icons.face_retouching_natural_rounded,
                  onTap: () => viewModel.identifyPerson(),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: AccessibleQuadrantTile(
                  title: "LOST ITEM",
                  subtitle: "Ground & Drop Scan",
                  icon: Icons.location_searching_rounded,
                  onTap: () => viewModel.findLostItem(),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSpokenAlertBar(GlassesStatus status) {
    return Semantics(
      liveRegion: true,
      label: "Current alert: ${status.lastSpokenAlert}",
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: AppTheme.darkSurface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.crispWhite, width: 1.5),
        ),
        child: Row(
          children: [
            const Icon(Icons.volume_up_rounded, color: AppTheme.tactileYellow, size: 24),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                status.lastSpokenAlert.isEmpty ? "System Standby" : status.lastSpokenAlert,
                style: const TextStyle(
                  color: AppTheme.crispWhite,
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
