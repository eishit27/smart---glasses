import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/app_theme.dart';
import '../../core/accessible_widgets.dart';
import 'face_enrollment_view_model.dart';

/// Screen for managing and enrolling known faces (family, friends, caregivers)
class FaceEnrollmentView extends StatelessWidget {
  const FaceEnrollmentView({super.key});

  @override
  Widget build(BuildContext context) {
    final viewModel = context.watch<FaceEnrollmentViewModel>();

    return Scaffold(
      backgroundColor: AppTheme.pureBlack,
      appBar: AppBar(
        title: const Text("KNOWN FACES"),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const AccessibleHeader(title: "FAMILY & FRIENDS DIRECTORY"),
              const SizedBox(height: 8),
              const Text(
                "When your glasses detect an enrolled person, their name and direction will be whispered to you automatically.",
                style: TextStyle(
                  color: AppTheme.crispWhite,
                  fontSize: 16,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 16),

              // ── Enrolled Faces List ─────────────────────────────────────────
              Expanded(
                child: viewModel.isLoading
                    ? const Center(
                        child: CircularProgressIndicator(color: AppTheme.tactileYellow),
                      )
                    : viewModel.faces.isEmpty
                        ? _buildEmptyState()
                        : ListView.separated(
                            itemCount: viewModel.faces.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 12),
                            itemBuilder: (context, index) {
                              final face = viewModel.faces[index];
                              return _buildFaceCard(context, viewModel, face.id, face.name, face.relationship);
                            },
                          ),
              ),
              const SizedBox(height: 16),

              // ── Enroll New Person Button ────────────────────────────────────
              AccessibleButton(
                label: "+ ENROLL NEW PERSON",
                semanticLabel: "Enroll new person. Open form to add family member or friend.",
                icon: Icons.person_add_alt_1_rounded,
                onPressed: () => _showEnrollDialog(context, viewModel),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: AppTheme.darkSurface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.tactileYellow, width: 2),
        ),
        child: const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.people_outline_rounded, size: 64, color: AppTheme.tactileYellow),
            SizedBox(height: 16),
            Text(
              "No Faces Enrolled Yet",
              style: TextStyle(
                color: AppTheme.tactileYellow,
                fontSize: 22,
                fontWeight: FontWeight.w900,
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 8),
            Text(
              "Tap 'Enroll New Person' below to add family members, caregivers, or friends.",
              style: TextStyle(
                color: AppTheme.crispWhite,
                fontSize: 16,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFaceCard(
    BuildContext context,
    FaceEnrollmentViewModel viewModel,
    String id,
    String name,
    String relationship,
  ) {
    return Semantics(
      label: "$name, relationship: $relationship. Swipe right to delete.",
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.darkSurface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.tactileYellow, width: 2.5),
        ),
        child: Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: AppTheme.pureBlack,
                shape: BoxShape.circle,
                border: Border.all(color: AppTheme.tactileYellow, width: 2),
              ),
              child: const Icon(
                Icons.person,
                color: AppTheme.tactileYellow,
                size: 32,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: const TextStyle(
                      color: AppTheme.tactileYellow,
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    relationship,
                    style: const TextStyle(
                      color: AppTheme.crispWhite,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.delete_forever_rounded, color: AppTheme.statusRed, size: 32),
              tooltip: "Delete $name from face database",
              onPressed: () => _showDeleteConfirmDialog(context, viewModel, id, name),
            ),
          ],
        ),
      ),
    );
  }

  void _showDeleteConfirmDialog(
    BuildContext context,
    FaceEnrollmentViewModel viewModel,
    String id,
    String name,
  ) {
    showDialog(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        backgroundColor: AppTheme.pureBlack,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: AppTheme.statusRed, width: 2.5),
        ),
        title: Text(
          "Delete $name?",
          style: const TextStyle(color: AppTheme.statusRed, fontWeight: FontWeight.bold),
        ),
        content: Text(
          "Are you sure you want to remove $name? The glasses will no longer announce their name.",
          style: const TextStyle(color: AppTheme.crispWhite, fontSize: 16),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogCtx),
            child: const Text("CANCEL", style: TextStyle(color: AppTheme.crispWhite, fontSize: 16)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.statusRed),
            onPressed: () {
              Navigator.pop(dialogCtx);
              viewModel.removeFace(id, name);
            },
            child: const Text("DELETE", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _showEnrollDialog(BuildContext context, FaceEnrollmentViewModel viewModel) {
    final nameController = TextEditingController();
    final relationController = TextEditingController();

    showDialog(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        backgroundColor: AppTheme.pureBlack,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: AppTheme.tactileYellow, width: 2.5),
        ),
        title: const Text(
          "Enroll New Person",
          style: TextStyle(color: AppTheme.tactileYellow, fontWeight: FontWeight.w900),
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                autofocus: true,
                style: const TextStyle(color: AppTheme.crispWhite, fontSize: 18),
                decoration: InputDecoration(
                  labelText: "Full Name",
                  labelStyle: const TextStyle(color: AppTheme.tactileYellow),
                  hintText: "e.g., Sarah Smith",
                  hintStyle: const TextStyle(color: Colors.grey),
                  enabledBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: AppTheme.tactileYellow, width: 2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: AppTheme.crispWhite, width: 2.5),
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: relationController,
                style: const TextStyle(color: AppTheme.crispWhite, fontSize: 18),
                decoration: InputDecoration(
                  labelText: "Relationship / Role",
                  labelStyle: const TextStyle(color: AppTheme.tactileYellow),
                  hintText: "e.g., Mother, Doctor, Coworker",
                  hintStyle: const TextStyle(color: Colors.grey),
                  enabledBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: AppTheme.tactileYellow, width: 2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: AppTheme.crispWhite, width: 2.5),
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogCtx),
            child: const Text("CANCEL", style: TextStyle(color: AppTheme.crispWhite, fontSize: 16)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.tactileYellow),
            onPressed: () {
              if (nameController.text.trim().isNotEmpty) {
                viewModel.enrollFace(
                  name: nameController.text.trim(),
                  relationship: relationController.text.trim(),
                  photoPath: "",
                );
                Navigator.pop(dialogCtx);
              }
            },
            child: const Text("ENROLL", style: TextStyle(color: AppTheme.pureBlack, fontWeight: FontWeight.w900)),
          ),
        ],
      ),
    );
  }
}
