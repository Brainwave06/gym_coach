import 'package:flutter/material.dart';
import 'core/constants.dart';
import 'core/theme.dart';
import 'ui/navigation/app_router.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppConstants.init();
  runApp(const FitPathApp());
}

class FitPathApp extends StatelessWidget {
  const FitPathApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'FitPath AI - Computer Vision & Gym Coach',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      routerConfig: appRouter,
    );
  }
}
