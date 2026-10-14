import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'data/services/ble_service.dart';
import 'domain/repositories/glasses_repository.dart';
import 'ui/core/app_theme.dart';
import 'ui/features/home/home_view.dart';
import 'ui/features/home/home_view_model.dart';
import 'ui/features/faces/face_enrollment_view_model.dart';
import 'ui/features/settings/settings_view_model.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Core Services & Domain Repositories
  final bleService = BLEService();
  final glassesRepository = GlassesRepository(bleService: bleService);

  runApp(
    VisionAidApp(
      bleService: bleService,
      repository: glassesRepository,
    ),
  );
}

class VisionAidApp extends StatelessWidget {
  final BLEService bleService;
  final GlassesRepository repository;

  const VisionAidApp({
    super.key,
    required this.bleService,
    required this.repository,
  });

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<BLEService>.value(value: bleService),
        Provider<GlassesRepository>.value(value: repository),
        ChangeNotifierProvider(
          create: (ctx) => HomeViewModel(repository: repository),
        ),
        ChangeNotifierProvider(
          create: (ctx) => FaceEnrollmentViewModel(repository: repository),
        ),
        ChangeNotifierProvider(
          create: (ctx) => SettingsViewModel(repository: repository),
        ),
      ],
      child: Consumer<SettingsViewModel>(
        builder: (context, settingsVm, child) {
          final isHighContrast = settingsVm.settings.highContrastTheme;

          return MaterialApp(
            title: 'VisionAid Companion',
            debugShowCheckedModeBanner: false,
            theme: isHighContrast
                ? AppTheme.highContrastTheme
                : AppTheme.standardDarkTheme,
            home: const HomeView(),
          );
        },
      ),
    );
  }
}
