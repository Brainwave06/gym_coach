import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'core/constants.dart';
import 'core/theme.dart';
import 'data/services/api_service.dart';
import 'ui/navigation/app_router.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppConstants.init();
  final isLoggedIn = await ApiService().restoreSavedSession();
  final router = createAppRouter(initialLocation: isLoggedIn ? '/dashboard' : '/welcome');
  runApp(FitPathApp(router: router));
}

class FitPathApp extends StatelessWidget {
  final GoRouter? router;
  const FitPathApp({super.key, this.router});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'FitPath AI - Computer Vision & Gym Coach',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      routerConfig: router ?? appRouter,
    );
  }
}
