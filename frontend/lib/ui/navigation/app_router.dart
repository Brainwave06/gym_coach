import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme.dart';
import '../features/auth/auth_screen.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/workout/exercise_catalog_screen.dart';
import '../features/workout/live_workout_screen.dart';
import '../features/chat/chat_screen.dart';
import '../features/meals/meal_logger_screen.dart';
import '../features/onboarding/welcome_screen.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>();

GoRouter createAppRouter({String initialLocation = '/welcome'}) => GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: initialLocation,
  routes: [
    GoRoute(
      path: '/welcome',
      builder: (context, state) => const WelcomeScreen(),
    ),
    GoRoute(
      path: '/auth',
      builder: (context, state) {
        final mode = state.uri.queryParameters['mode'];
        return AuthScreen(initialIsLogin: mode != 'register');
      },
    ),
    StatefulShellRoute.indexedStack(
      builder: (context, state, navigationShell) {
        return ScaffoldWithNavBar(navigationShell: navigationShell);
      },
      branches: [
        // 1. Dashboard Tab
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/dashboard',
              builder: (context, state) => const DashboardScreen(),
            ),
          ],
        ),
        // 2. Workout Tab
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/workout',
              builder: (context, state) => const ExerciseCatalogScreen(),
              routes: [
                GoRoute(
                  path: ':exercise_id',
                  parentNavigatorKey: _rootNavigatorKey,
                  builder: (context, state) => LiveWorkoutScreen(
                    exerciseId: state.pathParameters['exercise_id'] ?? 'squat',
                  ),
                ),
              ],
            ),
          ],
        ),
        // 3. Chat Tab
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/chat',
              builder: (context, state) => const ChatScreen(),
            ),
          ],
        ),
        // 4. Meals Tab
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/meals',
              builder: (context, state) => const MealLoggerScreen(),
            ),
          ],
        ),
      ],
    ),
  ],
);

final GoRouter appRouter = createAppRouter();

class ScaffoldWithNavBar extends StatelessWidget {
  final StatefulNavigationShell navigationShell;

  const ScaffoldWithNavBar({
    super.key,
    required this.navigationShell,
  });

  void _onDestinationSelected(int index) {
    navigationShell.goBranch(
      index,
      initialLocation: index == navigationShell.currentIndex,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: AppTheme.surface,
          border: Border(
            top: BorderSide(color: AppTheme.cardBorder, width: 1),
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF1B224B).withOpacity(0.04),
              blurRadius: 16,
              offset: const Offset(0, -4),
            ),
          ],
        ),
        child: NavigationBar(
          selectedIndex: navigationShell.currentIndex,
          onDestinationSelected: _onDestinationSelected,
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.dashboard_outlined),
              selectedIcon: Icon(Icons.dashboard_rounded, color: AppTheme.primary),
              label: 'Dashboard',
            ),
            NavigationDestination(
              icon: Icon(Icons.fitness_center_outlined),
              selectedIcon: Icon(Icons.fitness_center_rounded, color: AppTheme.primary),
              label: 'Workouts',
            ),
            NavigationDestination(
              icon: Icon(Icons.chat_bubble_outline_rounded),
              selectedIcon: Icon(Icons.chat_bubble_rounded, color: AppTheme.primary),
              label: 'Coach AI',
            ),
            NavigationDestination(
              icon: Icon(Icons.restaurant_outlined),
              selectedIcon: Icon(Icons.restaurant_rounded, color: AppTheme.primary),
              label: 'Meals',
            ),
          ],
        ),
      ),
    );
  }
}
