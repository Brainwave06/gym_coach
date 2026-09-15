import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants.dart';
import '../../../core/theme.dart';
import '../../widgets/glass_card.dart';
import '../../widgets/squircle_icon_card.dart';

class ExerciseCatalogScreen extends StatefulWidget {
  const ExerciseCatalogScreen({super.key});

  @override
  State<ExerciseCatalogScreen> createState() => _ExerciseCatalogScreenState();
}

class _ExerciseCatalogScreenState extends State<ExerciseCatalogScreen> {
  String _selectedFilter = 'All';

  final List<String> _filters = ['All', 'Compound', 'Hypertrophy', 'Bodyweight', 'Arms'];

  @override
  Widget build(BuildContext context) {
    final filteredExercises = AppConstants.exercises.where((ex) {
      if (_selectedFilter == 'All') return true;
      return ex['category']!.toLowerCase().contains(_selectedFilter.toLowerCase());
    }).toList();

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text(
          'Exercise Catalog',
          style: TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 20,
            fontWeight: FontWeight.w800,
            letterSpacing: -0.4,
          ),
        ),
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Filter Chips Horizontal Bar
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            child: Row(
              children: _filters.map((filter) {
                final isSelected = _selectedFilter == filter;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: GestureDetector(
                    onTap: () => setState(() => _selectedFilter = filter),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
                      decoration: BoxDecoration(
                        color: isSelected ? AppTheme.primary : AppTheme.surfaceWarm,
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(
                          color: isSelected
                              ? AppTheme.primary
                              : AppTheme.surfaceWarmBorder.withOpacity(0.6),
                        ),
                        boxShadow: isSelected ? AppTheme.buttonShadow : null,
                      ),
                      child: Text(
                        filter,
                        style: TextStyle(
                          color: isSelected ? Colors.white : AppTheme.textPrimary,
                          fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),

          // Exercise Items List
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              itemCount: filteredExercises.length,
              separatorBuilder: (context, index) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final ex = filteredExercises[index];
                final id = ex['id']!;
                final name = ex['name']!;
                final category = ex['category']!;

                return GlassCard(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  onTap: () => context.go('/workout/$id'),
                  child: Row(
                    children: [
                      // Warm Sand Squircle Icon
                      const SquircleIconCard(
                        icon: Icons.fitness_center_rounded,
                        size: 48,
                        iconSize: 22,
                      ),
                      const SizedBox(width: 14),
                      // Exercise Name & Category
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              name,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 15,
                                color: AppTheme.textPrimary,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              category,
                              style: const TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                      // Start Camera Pill Button
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceWarm,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: AppTheme.surfaceWarmBorder.withOpacity(0.8),
                          ),
                        ),
                        child: const Row(
                          children: [
                            Icon(
                              Icons.videocam_rounded,
                              size: 16,
                              color: AppTheme.primary,
                            ),
                            SizedBox(width: 6),
                            Text(
                              'Start',
                              style: TextStyle(
                                color: AppTheme.primary,
                                fontWeight: FontWeight.w700,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
