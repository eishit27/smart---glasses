import 'package:flutter/foundation.dart';
import '../../../data/models/face_profile.dart';
import '../../../data/services/audio_feedback_service.dart';
import '../../../domain/repositories/glasses_repository.dart';

/// ViewModel managing known faces database, biometric tagging, and enrollment
class FaceEnrollmentViewModel extends ChangeNotifier {
  final GlassesRepository _repository;
  List<FaceProfile> _faces = [];
  bool _isLoading = false;

  FaceEnrollmentViewModel({required GlassesRepository repository})
      : _repository = repository {
    loadFaces();
  }

  List<FaceProfile> get faces => _faces;
  bool get isLoading => _isLoading;

  Future<void> loadFaces() async {
    _isLoading = true;
    notifyListeners();
    try {
      _faces = await _repository.loadEnrolledFaces();
    } catch (e) {
      debugPrint("Error loading faces: $e");
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> enrollFace({
    required String name,
    required String relationship,
    required String photoPath,
  }) async {
    if (name.trim().isEmpty) return;

    final newProfile = FaceProfile(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      name: name.trim(),
      relationship: relationship.trim().isEmpty ? "Friend" : relationship.trim(),
      enrolledAt: DateTime.now(),
      photoPath: photoPath,
    );

    await _repository.saveEnrolledFace(newProfile);
    _faces.add(newProfile);
    AudioFeedbackService.announceForAccessibility("Enrolled $name as $relationship successfully");
    AudioFeedbackService.triggerHapticSuccess();
    notifyListeners();
  }

  Future<void> removeFace(String id, String name) async {
    await _repository.deleteEnrolledFace(id);
    _faces.removeWhere((f) => f.id == id);
    AudioFeedbackService.announceForAccessibility("Removed $name from face database");
    AudioFeedbackService.triggerHapticWarning();
    notifyListeners();
  }
}
