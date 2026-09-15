import 'package:flutter/material.dart';
import 'core/theme.dart';
import 'ui/navigation/app_router.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
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
