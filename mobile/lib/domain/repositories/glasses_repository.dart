import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../data/models/glasses_status.dart';
import '../../data/models/face_profile.dart';
import '../../data/models/user_settings.dart';
import '../../data/services/ble_service.dart';

class GlassesRepository {
  final BLEService _bleService;
  GlassesRepository({required BLEService bleService}) : _bleService = bleService;

  Stream<GlassesStatus> get statusStream => _bleService.statusStream;
  GlassesStatus get currentStatus => _bleService.currentStatus;

  Future<void> connectGlasses(String token) async {
    await _bleService.startAutoConnect(pairingToken: token);
  }

  Future<void> disconnectGlasses() async {
    await _bleService.disconnect();
  }

  Future<void> triggerScanScene() async {
    await _bleService.sendCommand(1); // 1 = describe scene
  }

  Future<void> triggerReadText() async {
    await _bleService.sendCommand(2); // 2 = OCR read
  }

  Future<void> triggerFindFaces() async {
    await _bleService.sendCommand(3); // 3 = identify person
  }

  // ── Face Database Storage ────────────────────────────────────────────────
  Future<List<FaceProfile>> loadEnrolledFaces() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonString = prefs.getString('enrolled_faces');
    if (jsonString == null) return [];

    try {
      final List<dynamic> list = json.decode(jsonString);
      return list.map((item) => FaceProfile.fromJson(item)).toList();
    } catch (e) {
      debugPrint("Error loading faces: $e");
      return [];
    }
  }

  Future<void> saveEnrolledFace(FaceProfile profile) async {
    final current = await loadEnrolledFaces();
    current.add(profile);

    final prefs = await SharedPreferences.getInstance();
    final jsonString = json.encode(current.map((f) => f.toJson()).toList());
    await prefs.setString('enrolled_faces', jsonString);
  }

  Future<void> deleteEnrolledFace(String id) async {
    final current = await loadEnrolledFaces();
    current.removeWhere((f) => f.id == id);

    final prefs = await SharedPreferences.getInstance();
    final jsonString = json.encode(current.map((f) => f.toJson()).toList());
    await prefs.setString('enrolled_faces', jsonString);
  }

  // ── Settings Storage ─────────────────────────────────────────────────────
  Future<UserSettings> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    return UserSettings(
      speechRate: prefs.getDouble('speech_rate') ?? 1.0,
      volume: prefs.getDouble('volume') ?? 1.0,
      enableRunningMode: prefs.getBool('running_mode') ?? true,
      enableAudioEarcons: prefs.getBool('audio_earcons') ?? true,
      highContrastTheme: prefs.getBool('high_contrast') ?? true,
      emergencyContactName: prefs.getString('emergency_name') ?? "",
      emergencyPhone: prefs.getString('emergency_phone') ?? "",
    );
  }

  Future<void> saveSettings(UserSettings settings) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('speech_rate', settings.speechRate);
    await prefs.setDouble('volume', settings.volume);
    await prefs.setBool('running_mode', settings.enableRunningMode);
    await prefs.setBool('audio_earcons', settings.enableAudioEarcons);
    await prefs.setBool('high_contrast', settings.highContrastTheme);
    await prefs.setString('emergency_name', settings.emergencyContactName);
    await prefs.setString('emergency_phone', settings.emergencyPhone);
  }
}
