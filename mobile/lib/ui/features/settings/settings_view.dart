import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/app_theme.dart';
import '../../core/accessible_widgets.dart';
import 'settings_view_model.dart';

/// Screen for accessibility preferences, voice speed, motion modes, and emergency SOS
class SettingsView extends StatefulWidget {
  const SettingsView({super.key});

  @override
  State<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends State<SettingsView> {
  late TextEditingController _sosNameController;
  late TextEditingController _sosPhoneController;
  late TextEditingController _tokenController;

  @override
  void initState() {
    super.initState();
    final settings = context.read<SettingsViewModel>().settings;
    _sosNameController = TextEditingController(text: settings.emergencyContactName);
    _sosPhoneController = TextEditingController(text: settings.emergencyPhone);
    _tokenController = TextEditingController(text: settings.pairingToken);
  }

  @override
  void dispose() {
    _sosNameController.dispose();
    _sosPhoneController.dispose();
    _tokenController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final viewModel = context.watch<SettingsViewModel>();
    final settings = viewModel.settings;

    return Scaffold(
      backgroundColor: AppTheme.pureBlack,
      appBar: AppBar(
        title: const Text("SETTINGS & SAFETY"),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16.0),
          children: [
            // ── Section 1: Audio & Voice ──────────────────────────────────────
            const AccessibleHeader(title: "AUDIO & VOICE"),
            const SizedBox(height: 8),
            _buildSettingCard(
              title: "Speech Rate: ${settings.speechRate.toStringAsFixed(1)}x",
              subtitle: "Speed of audio descriptions and navigation alerts",
              child: Slider(
                value: settings.speechRate,
                min: 0.5,
                max: 2.5,
                divisions: 20,
                label: "${settings.speechRate.toStringAsFixed(1)}x",
                onChanged: (val) => viewModel.updateSpeechRate(val),
              ),
            ),
            const SizedBox(height: 12),
            _buildSwitchCard(
              title: "Directional Audio Radar",
              subtitle: "Sub-30ms 3D acoustic beeps for immediate proximity hazards",
              value: settings.enableAudioEarcons,
              onChanged: (val) => viewModel.toggleAudioEarcons(val),
            ),

            const SizedBox(height: 24),
            // ── Section 2: Motion & Safety ────────────────────────────────────
            const AccessibleHeader(title: "MOBILITY MODES"),
            const SizedBox(height: 8),
            _buildSwitchCard(
              title: "Motion-Adaptive Running Mode",
              subtitle: "Expands safety horizon to 6.5m and boosts 8ms turbo vision when jogging or running",
              value: settings.enableRunningMode,
              onChanged: (val) => viewModel.toggleRunningMode(val),
            ),

            const SizedBox(height: 24),
            // ── Section 3: Emergency SOS ──────────────────────────────────────
            const AccessibleHeader(title: "EMERGENCY SOS CONTACT"),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.darkSurface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.statusRed, width: 2.5),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    "Triple-click the glasses temple button to instantly send location and emergency alert to this contact.",
                    style: TextStyle(color: AppTheme.crispWhite, fontSize: 15),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _sosNameController,
                    style: const TextStyle(color: AppTheme.crispWhite, fontSize: 16),
                    decoration: InputDecoration(
                      labelText: "Contact Name",
                      labelStyle: const TextStyle(color: AppTheme.tactileYellow),
                      enabledBorder: OutlineInputBorder(
                        borderSide: const BorderSide(color: AppTheme.tactileYellow, width: 1.5),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderSide: const BorderSide(color: AppTheme.crispWhite, width: 2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _sosPhoneController,
                    keyboardType: TextInputType.phone,
                    style: const TextStyle(color: AppTheme.crispWhite, fontSize: 16),
                    decoration: InputDecoration(
                      labelText: "Phone Number",
                      labelStyle: const TextStyle(color: AppTheme.tactileYellow),
                      enabledBorder: OutlineInputBorder(
                        borderSide: const BorderSide(color: AppTheme.tactileYellow, width: 1.5),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderSide: const BorderSide(color: AppTheme.crispWhite, width: 2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  AccessibleButton(
                    label: "SAVE EMERGENCY CONTACT",
                    height: 52,
                    fontSize: 16,
                    backgroundColor: AppTheme.statusRed,
                    foregroundColor: Colors.white,
                    borderColor: Colors.white,
                    onPressed: () {
                      viewModel.updateEmergencyContact(
                        _sosNameController.text,
                        _sosPhoneController.text,
                      );
                    },
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),
            // ── Section 4: Hardware & Security ────────────────────────────────
            const AccessibleHeader(title: "HARDWARE PAIRING & SECURITY"),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.darkSurface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.tactileYellow, width: 2.0),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    "Security Handshake Token",
                    style: TextStyle(
                      color: AppTheme.tactileYellow,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    "Glasses disconnect unauthenticated rogue devices after 10 seconds unless they present this token.",
                    style: TextStyle(color: AppTheme.crispWhite, fontSize: 14),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _tokenController,
                    style: const TextStyle(color: AppTheme.crispWhite, fontSize: 16),
                    decoration: InputDecoration(
                      labelText: "BLE Pairing Secret",
                      labelStyle: const TextStyle(color: AppTheme.tactileYellow),
                      enabledBorder: OutlineInputBorder(
                        borderSide: const BorderSide(color: AppTheme.tactileYellow, width: 1.5),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderSide: const BorderSide(color: AppTheme.crispWhite, width: 2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  AccessibleButton(
                    label: "UPDATE PAIRING TOKEN",
                    height: 52,
                    fontSize: 16,
                    onPressed: () {
                      viewModel.updatePairingToken(_tokenController.text);
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildSettingCard({
    required String title,
    required String subtitle,
    required Widget child,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.darkSurface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.tactileYellow, width: 2.0),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: AppTheme.tactileYellow,
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: const TextStyle(color: AppTheme.crispWhite, fontSize: 14),
          ),
          const SizedBox(height: 8),
          child,
        ],
      ),
    );
  }

  Widget _buildSwitchCard({
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.darkSurface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.tactileYellow, width: 2.0),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: AppTheme.tactileYellow,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(color: AppTheme.crispWhite, fontSize: 14),
                ),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
          ),
        ],
      ),
    );
  }
}
