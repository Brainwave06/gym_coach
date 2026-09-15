import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme.dart';
import '../../../data/models/app_models.dart';
import '../../../data/services/api_service.dart';
import '../../widgets/glass_card.dart';

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
    final goal = _profile?.goal ?? 'Muscle Building & Strength';

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppTheme.primary.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.flash_on, color: AppTheme.primary, size: 20),
            ),
            const SizedBox(width: 10),
            const Text('FITPATH'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: AppTheme.textSecondary),
            onPressed: _loadData,
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: AppTheme.textSecondary),
            onPressed: () {
              ApiService().logout();
              context.go('/auth');
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
          : RefreshIndicator(
              onRefresh: _loadData,
              color: AppTheme.primary,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Athlete Welcome Header
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Hey, $userName! 👋',
                              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Goal: ${goal.toUpperCase()}',
                              style: const TextStyle(fontSize: 13, color: AppTheme.primary, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceElevated,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: AppTheme.primary.withOpacity(0.3)),
                          ),
                          child: const Row(
                            children: [
                              Icon(Icons.local_fire_department, color: Colors.orange, size: 16),
                              SizedBox(width: 4),
                              Text('3 Day Streak', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),

                    // Biometrics Grid
                    const Text('DAILY TARGETS & BIOMETRICS', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textSecondary, letterSpacing: 1)),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: GlassCard(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Row(
                                  children: [
                                    Icon(Icons.monitor_weight_outlined, size: 16, color: AppTheme.secondary),
                                    SizedBox(width: 6),
                                    Text('Body Mass', style: TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  '${_profile?.weightKg.toStringAsFixed(1) ?? "70.0"} kg',
                                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                                ),
                                const SizedBox(height: 4),
                                Text('BMI ${bio?.bmi ?? 22.0} (${bio?.bmiCategory ?? "Normal"})', style: const TextStyle(fontSize: 11, color: AppTheme.secondary)),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: GlassCard(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Row(
                                  children: [
                                    Icon(Icons.bolt, size: 16, color: Colors.orange),
                                    SizedBox(width: 6),
                                    Text('Daily Burn', style: TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  '${bio?.tdeeKcal ?? 2200} kcal',
                                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                                ),
                                const SizedBox(height: 4),
                                Text('BMR: ${bio?.bmrKcal ?? 1700} kcal', style: const TextStyle(fontSize: 11, color: Colors.orange)),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Protein Target Card
                    GlassCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.restaurant_menu, color: AppTheme.primary, size: 18),
                                  SizedBox(width: 8),
                                  Text('Target Protein Intake', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                                ],
                              ),
                              Text(
                                '${bio?.proteinTargetG.toInt() ?? 140}g / day',
                                style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.w900, fontSize: 16),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: const LinearProgressIndicator(
                              value: 0.65,
                              minHeight: 10,
                              backgroundColor: AppTheme.surfaceElevated,
                              valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primary),
                            ),
                          ),
                          const SizedBox(height: 8),
                          const Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text('92g consumed so far', style: TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
                              Text('48g remaining', style: TextStyle(fontSize: 12, color: AppTheme.primary)),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Today's Assigned Workout Card
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text("TODAY'S WORKOUT PLAN", style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textSecondary, letterSpacing: 1)),
                        TextButton.icon(
                          onPressed: () => context.go('/workout'),
                          icon: const Icon(Icons.arrow_forward, size: 14, color: AppTheme.primary),
                          label: const Text('All Exercises', style: TextStyle(fontSize: 12, color: AppTheme.primary)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),

                    GlassCard(
                      borderColor: AppTheme.primary.withOpacity(0.3),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: AppTheme.primary.withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: const Icon(Icons.fitness_center, color: AppTheme.primary, size: 24),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      _planData?['plan_name']?.toString() ?? 'Daily Strength & Hypertrophy',
                                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      (_planData?['plan'] as List<dynamic>?)
                                              ?.map((e) => (e['exercise_id'] ?? '').toString().toUpperCase())
                                              .where((s) => s.isNotEmpty)
                                              .join(' • ') ??
                                          'Squat • Overhead Press • Plank',
                                      style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 18),
                          const Divider(height: 1, color: Colors.white10),
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceAround,
                            children: [
                              _buildMetricItem('Exercises', '4 moves'),
                              _buildMetricItem('Est. Duration', '25 min'),
                              _buildMetricItem('AI Tracking', 'Active'),
                            ],
                          ),
                          const SizedBox(height: 20),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: () => context.go('/workout/squat'),
                              icon: const Icon(Icons.videocam, color: Colors.black),
                              label: const Text('Start Camera Workout'),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Quick Actions
                    const Text('QUICK ACCESS', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textSecondary, letterSpacing: 1)),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: GlassCard(
                            onTap: () => context.go('/meals'),
                            child: const Column(
                              children: [
                                Icon(Icons.camera_alt, color: AppTheme.secondary, size: 30),
                                SizedBox(height: 8),
                                Text('Scan Food Plate', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                SizedBox(height: 4),
                                Text('Vision AI Macros', style: TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: GlassCard(
                            onTap: () => context.go('/chat'),
                            child: const Column(
                              children: [
                                Icon(Icons.chat_bubble, color: AppTheme.primary, size: 30),
                                SizedBox(height: 8),
                                Text('Ask Gym Coach', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                SizedBox(height: 4),
                                Text('AI Assistant', style: TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildMetricItem(String label, String value) {
    return Column(
      children: [
        Text(value, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
        const SizedBox(height: 2),
        Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
      ],
    );
  }
}
