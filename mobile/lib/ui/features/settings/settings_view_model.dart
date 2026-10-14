import 'package:flutter/foundation.dart';
import '../../../data/models/user_settings.dart';
import '../../../data/services/audio_feedback_service.dart';
import '../../../domain/repositories/glasses_repository.dart';

/// ViewModel managing user accessibility preferences, audio speed, and emergency contacts
class SettingsViewModel extends ChangeNotifier {
  final GlassesRepository _repository;
  UserSettings _settings = const UserSettings();
  bool _isLoading = true;

  SettingsViewModel({required GlassesRepository repository})
      : _repository = repository {
    loadSettings();
  }

  UserSettings get settings => _settings;
  bool get isLoading => _isLoading;

  Future<void> loadSettings() async {
    _isLoading = true;
    notifyListeners();
    try {
      _settings = await _repository.loadSettings();
    } catch (e) {
      debugPrint("Error loading settings: $e");
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> updateSpeechRate(double rate) async {
    _settings = _settings.copyWith(speechRate: rate);
    await _repository.saveSettings(_settings);
    AudioFeedbackService.announceForAccessibility("Speech rate set to ${rate.toStringAsFixed(1)} times");
    notifyListeners();
  }

  Future<void> updateVolume(double volume) async {
    _settings = _settings.copyWith(volume: volume);
    await _repository.saveSettings(_settings);
    AudioFeedbackService.announceForAccessibility("Audio volume set to ${(volume * 100).toInt()} percent");
    notifyListeners();
  }

  Future<void> toggleRunningMode(bool enabled) async {
    _settings = _settings.copyWith(enableRunningMode: enabled);
    await _repository.saveSettings(_settings);
    AudioFeedbackService.announceForAccessibility(
      enabled ? "Dynamic Running Mode enabled" : "Dynamic Running Mode disabled",
    );
    AudioFeedbackService.triggerHapticClick();
    notifyListeners();
  }

  Future<void> toggleAudioEarcons(bool enabled) async {
    _settings = _settings.copyWith(enableAudioEarcons: enabled);
    await _repository.saveSettings(_settings);
    AudioFeedbackService.announceForAccessibility(
      enabled ? "Directional audio radar beeps enabled" : "Directional audio radar beeps disabled",
    );
    AudioFeedbackService.triggerHapticClick();
    notifyListeners();
  }

  Future<void> toggleHighContrast(bool enabled) async {
    _settings = _settings.copyWith(highContrastTheme: enabled);
    await _repository.saveSettings(_settings);
    AudioFeedbackService.announceForAccessibility(
      enabled ? "High contrast mode enabled" : "High contrast mode disabled",
    );
    AudioFeedbackService.triggerHapticClick();
    notifyListeners();
  }

  Future<void> updateEmergencyContact(String name, String phone) async {
    _settings = _settings.copyWith(
      emergencyContactName: name.trim(),
      emergencyPhone: phone.trim(),
    );
    await _repository.saveSettings(_settings);
    AudioFeedbackService.announceForAccessibility("Emergency SOS contact saved");
    AudioFeedbackService.triggerHapticSuccess();
    notifyListeners();
  }

  Future<void> updatePairingToken(String token) async {
    _settings = _settings.copyWith(pairingToken: token.trim());
    await _repository.saveSettings(_settings);
    AudioFeedbackService.announceForAccessibility("Pairing security token updated");
    AudioFeedbackService.triggerHapticSuccess();
    notifyListeners();
  }
}
