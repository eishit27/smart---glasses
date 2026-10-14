import 'dart:async';
import 'package:flutter/foundation.dart';
import '../../../data/models/glasses_status.dart';
import '../../../data/services/audio_feedback_service.dart';
import '../../../domain/repositories/glasses_repository.dart';

/// ViewModel managing home screen state, BLE lifecycle, and tactile actions
class HomeViewModel extends ChangeNotifier {
  final GlassesRepository _repository;
  StreamSubscription<GlassesStatus>? _statusSubscription;

  GlassesStatus _status = const GlassesStatus();
  GlassesStatus get status => _status;

  bool _isActionInProgress = false;
  bool get isActionInProgress => _isActionInProgress;

  String _lastActionStatus = "";
  String get lastActionStatus => _lastActionStatus;

  HomeViewModel({required GlassesRepository repository})
      : _repository = repository {
    _status = _repository.currentStatus;
    _statusSubscription = _repository.statusStream.listen((newStatus) {
      _status = newStatus;
      notifyListeners();
    });
  }

  String get connectionStatusAnnouncement {
    switch (_status.state) {
      case ConnectionState.connected:
        return "Glasses connected. Battery ${_status.batteryPercent} percent. ${_status.currentMode.name} mode active.";
      case ConnectionState.connecting:
        return "Connecting to VisionAid glasses...";
      case ConnectionState.scanning:
        return "Searching for VisionAid glasses...";
      case ConnectionState.authenticating:
        return "Verifying security handshake with glasses...";
      case ConnectionState.disconnected:
        return "Glasses disconnected. Double tap to reconnect.";
      case ConnectionState.error:
        return "Connection failed. Please ensure glasses are powered on.";
    }
  }

  Future<void> connect(String token) async {
    _lastActionStatus = "Searching for glasses...";
    AudioFeedbackService.announceForAccessibility("Connecting to glasses");
    notifyListeners();
    try {
      await _repository.connectGlasses(token);
    } catch (e) {
      _lastActionStatus = "Connection error";
      AudioFeedbackService.triggerHapticWarning();
      notifyListeners();
    }
  }

  Future<void> disconnect() async {
    await _repository.disconnectGlasses();
    AudioFeedbackService.announceForAccessibility("Glasses disconnected");
    notifyListeners();
  }

  Future<void> scanScene() async {
    if (_isActionInProgress) return;
    _isActionInProgress = true;
    _lastActionStatus = "Scanning surroundings...";
    notifyListeners();

    AudioFeedbackService.announceForAccessibility("Scanning scene");
    AudioFeedbackService.triggerHapticSuccess();
    await _repository.triggerScanScene();

    _isActionInProgress = false;
    notifyListeners();
  }

  Future<void> readText() async {
    if (_isActionInProgress) return;
    _isActionInProgress = true;
    _lastActionStatus = "Reading text...";
    notifyListeners();

    AudioFeedbackService.announceForAccessibility("Reading text");
    AudioFeedbackService.triggerHapticSuccess();
    await _repository.triggerReadText();

    _isActionInProgress = false;
    notifyListeners();
  }

  Future<void> identifyPerson() async {
    if (_isActionInProgress) return;
    _isActionInProgress = true;
    _lastActionStatus = "Identifying person...";
    notifyListeners();

    AudioFeedbackService.announceForAccessibility("Identifying people");
    AudioFeedbackService.triggerHapticSuccess();
    await _repository.triggerFindFaces();

    _isActionInProgress = false;
    notifyListeners();
  }

  Future<void> findLostItem() async {
    if (_isActionInProgress) return;
    _isActionInProgress = true;
    _lastActionStatus = "Scanning floor for dropped items...";
    notifyListeners();

    AudioFeedbackService.announceForAccessibility("Scanning ground for lost items");
    AudioFeedbackService.triggerHapticSuccess();
    // Command 4: ground plane drop scan
    await _repository.triggerScanScene();

    _isActionInProgress = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _statusSubscription?.cancel();
    super.dispose();
  }
}
