import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme.dart';
import '../../../data/models/app_models.dart';
import '../../../data/services/api_service.dart';
import '../../widgets/fitpath_logo.dart';
import '../../widgets/glass_card.dart';
import '../../widgets/squircle_icon_card.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  AthleteProfile? _profile;
  Map<String, dynamic>? _planData;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final api = ApiService();
    final profile = await api.getProfile();
    final plan = await api.getWorkoutPlan();
    if (mounted) {
      setState(() {
        _profile = profile;
        _planData = plan;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final bio = _profile?.biometrics;
    final userName = _profile?.name ?? ApiService().currentUser?.fullName ?? 'Athlete';
    final goal = _profile?.goal ?? 'Strength & Muscle Building';

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        titleSpacing: 20,
        title: const FitPathLogo(
          size: 32,
          showText: true,
          textStyle: TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 18,
            fontWeight: FontWeight.w800,
            letterSpacing: -0.4,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: AppTheme.textSecondary),
            onPressed: _loadData,
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: AppTheme.textSecondary),
            onPressed: () {
              ApiService().logout();
              context.go('/welcome');
            },
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primary),
              ),
            )
          : RefreshIndicator(
              onRefresh: _loadData,
              color: AppTheme.primary,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Athlete Welcome Header
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Hey, $userName 👋',
                                style: const TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.w800,
                                  color: AppTheme.textPrimary,
                                  letterSpacing: -0.5,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                goal,
                                style: const TextStyle(
                                  fontSize: 13,
                                  color: AppTheme.textSecondary,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                        // Warm Sand Streak Badge
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceWarm,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: AppTheme.surfaceWarmBorder.withOpacity(0.6),
                            ),
                          ),
                          child: const Row(
                            children: [
                              Icon(
                                Icons.local_fire_department_rounded,
                                color: Color(0xFFE65100),
                                size: 18,
                              ),
                              SizedBox(width: 6),
                              Text(
                                '3 Day Streak',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.textPrimary,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),

                    // Biometrics Section Header
                    const Text(
                      'DAILY TARGETS & BIOMETRICS',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textSecondary,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Two-Column Biometrics Cards
                    Row(
                      children: [
                        Expanded(
                          child: GlassCard(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      'Body Mass',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                        color: AppTheme.textSecondary,
                                      ),
                                    ),
                                    SquircleIconCard(
                                      icon: Icons.fitness_center_outlined,
                                      size: 36,
                                      iconSize: 18,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 10),
                                Text(
                                  '${_profile?.weightKg.toStringAsFixed(1) ?? "70.0"} kg',
                                  style: const TextStyle(
                                    fontSize: 22,
                                    fontWeight: FontWeight.w800,
                                    color: AppTheme.textPrimary,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'BMI ${bio?.bmi ?? 22.0} • ${bio?.bmiCategory ?? "Normal"}',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: AppTheme.primaryLight,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: GlassCard(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      'Daily Burn',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                        color: AppTheme.textSecondary,
                                      ),
                                    ),
                                    SquircleIconCard(
                                      icon: Icons.bolt_outlined,
                                      size: 36,
                                      iconSize: 18,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 10),
                                Text(
                                  '${bio?.tdeeKcal ?? 2200} kcal',
                                  style: const TextStyle(
                                    fontSize: 22,
                                    fontWeight: FontWeight.w800,
                                    color: AppTheme.textPrimary,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'BMR ${bio?.bmrKcal ?? 1700} kcal',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: AppTheme.accentGold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    // Target Protein Intake Card
                    GlassCard(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Row(
                                children: [
                                  SquircleIconCard(
                                    icon: Icons.restaurant_menu_rounded,
                                    size: 40,
                                    iconSize: 20,
                                  ),
                                  SizedBox(width: 12),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        'Target Protein',
                                        style: TextStyle(
                                          fontWeight: FontWeight.w700,
                                          fontSize: 15,
                                          color: AppTheme.textPrimary,
                                        ),
                                      ),
                                      Text(
                                        'Evidence-based athletic intake',
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: AppTheme.textSecondary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                              Text(
                                '${bio?.proteinTargetG.toInt() ?? 140}g / day',
                                style: const TextStyle(
                                  color: AppTheme.primary,
                                  fontWeight: FontWeight.w800,
                                  fontSize: 16,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(10),
                            child: LinearProgressIndicator(
                              value: 0.65,
                              minHeight: 10,
                              backgroundColor: AppTheme.surfaceWarm,
                              valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.primary),
                            ),
                          ),
                          const SizedBox(height: 10),
                          const Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                '92g consumed so far',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: AppTheme.textSecondary,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              Text(
                                '48g remaining',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: AppTheme.primary,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 26),

                    // Today's Assigned Workout Plan Card
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          "TODAY'S WORKOUT PLAN",
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textSecondary,
                            letterSpacing: 0.8,
                          ),
                        ),
                        GestureDetector(
                          onTap: () => context.go('/workout'),
                          child: const Row(
                            children: [
                              Text(
                                'All Exercises',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.primary,
                                ),
                              ),
                              SizedBox(width: 4),
                              Icon(
                                Icons.arrow_forward_rounded,
                                size: 14,
                                color: AppTheme.primary,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Luxury Workout Card
                    GlassCard(
                      padding: const EdgeInsets.all(22),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const SquircleIconCard(
                                icon: Icons.fitness_center_rounded,
                                size: 48,
                                iconSize: 24,
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      _planData?['plan_name']?.toString() ?? 'Strength & Hypertrophy Routine',
                                      style: const TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.w800,
                                        color: AppTheme.textPrimary,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      (_planData?['plan'] as List<dynamic>?)
                                              ?.map((e) => (e['exercise_id'] ?? '').toString().toUpperCase())
                                              .where((s) => s.isNotEmpty)
                                              .join(' • ') ??
                                          'SQUAT • OVERHEAD PRESS • PLANK',
                                      style: const TextStyle(
                                        fontSize: 12,
                                        color: AppTheme.textSecondary,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 18),
                          Divider(
                            height: 1,
                            color: AppTheme.surfaceWarmBorder.withOpacity(0.5),
                          ),
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceAround,
                            children: [
                              _buildMetricItem('Exercises', '4 moves'),
                              _buildMetricItem('Est. Duration', '25 min'),
                              _buildMetricItem('AI Pose Tracker', 'Active'),
                            ],
                          ),
                          const SizedBox(height: 20),
                          // Start Camera Workout Pill Button
                          Container(
                            height: 52,
                            width: double.infinity,
                            decoration: BoxDecoration(
                              gradient: AppTheme.primaryGradient,
                              borderRadius: BorderRadius.circular(30),
                              boxShadow: AppTheme.buttonShadow,
                            ),
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: () => context.go('/workout/squat'),
                                borderRadius: BorderRadius.circular(30),
                                splashColor: Colors.white.withOpacity(0.15),
                                child: const Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(
                                      Icons.videocam_rounded,
                                      color: Colors.white,
                                      size: 20,
                                    ),
                                    SizedBox(width: 10),
                                    Text(
                                      'Start Camera Workout',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 15,
                                        fontWeight: FontWeight.w700,
                                        letterSpacing: 0.2,
                                      ),
                                    ),
                                    SizedBox(width: 8),
                                    Icon(
                                      Icons.arrow_forward_rounded,
                                      color: Colors.white,
                                      size: 16,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Quick Actions Section
                    const Text(
                      'AI ASSISTANTS',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textSecondary,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: GlassCard(
                            onTap: () => context.go('/meals'),
                            padding: const EdgeInsets.all(18),
                            child: const Column(
                              children: [
                                SquircleIconCard(
                                  icon: Icons.filter_center_focus_rounded,
                                  size: 46,
                                  iconSize: 22,
                                ),
                                SizedBox(height: 10),
                                Text(
                                  'Scan Plate',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 14,
                                    color: AppTheme.textPrimary,
                                  ),
                                ),
                                SizedBox(height: 4),
                                Text(
                                  'Vision AI Macros',
                                  style: TextStyle(
                                    color: AppTheme.textSecondary,
                                    fontSize: 11,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: GlassCard(
                            onTap: () => context.go('/chat'),
                            padding: const EdgeInsets.all(18),
                            child: const Column(
                              children: [
                                SquircleIconCard(
                                  icon: Icons.chat_bubble_outline_rounded,
                                  size: 46,
                                  iconSize: 22,
                                ),
                                SizedBox(height: 10),
                                Text(
                                  'Gym AI Coach',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 14,
                                    color: AppTheme.textPrimary,
                                  ),
                                ),
                                SizedBox(height: 4),
                                Text(
                                  'Workout Debrief',
                                  style: TextStyle(
                                    color: AppTheme.textSecondary,
                                    fontSize: 11,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildMetricItem(String label, String value) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 15,
            color: AppTheme.textPrimary,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            color: AppTheme.textSecondary,
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}
