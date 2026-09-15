import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/sound_service.dart';
import '../../../core/theme.dart';
import '../../widgets/fitpath_logo.dart';
import '../../widgets/squircle_icon_card.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _floatController;

  @override
  void initState() {
    super.initState();
    // Gentle 3-second floating loop for the 4 squircle feature cards
    _floatController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _floatController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppTheme.warmBackgroundGradient,
        ),
        child: SafeArea(
          child: Column(
            children: [
              const SizedBox(height: 16),
              // Top Brand Header: Stylized F + "FitPath"
              const FitPathLogo(
                size: 46,
                showText: true,
              ),

              const SizedBox(height: 20),

              // Hero Headline
              const Text(
                'Smarter Training.\nBetter You.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                  height: 1.18,
                  letterSpacing: -0.8,
                ),
              ),

              const SizedBox(height: 12),

              // Subtitle
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 40),
                child: Text(
                  'Your personal fitness & nutrition\ncoach, in your pocket.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 14,
                    fontWeight: FontWeight.w400,
                    height: 1.45,
                  ),
                ),
              ),

              // Central Visual Hero with 4 Floating Squircle Feature Cards
              Expanded(
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final maxHeight = constraints.maxHeight;

                    return Center(
                      child: SizedBox(
                        width: 340,
                        height: maxHeight,
                        child: AnimatedBuilder(
                          animation: _floatController,
                          builder: (context, child) {
                            final double animVal = _floatController.value;
                            // Sinusoidal offsets with phase differences
                            final double float1 = math.sin(animVal * math.pi) * 8.0;
                            final double float2 = math.cos(animVal * math.pi) * 7.0;
                            final double float3 = math.sin((animVal + 0.5) * math.pi) * 8.0;
                            final double float4 = math.cos((animVal + 0.5) * math.pi) * 7.0;

                            return Stack(
                              alignment: Alignment.center,
                              clipBehavior: Clip.none,
                              children: [
                                // Center Athlete Image Hero
                                Positioned(
                                  top: 20,
                                  bottom: 20,
                                  child: Container(
                                    width: 220,
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(110),
                                      boxShadow: [
                                        BoxShadow(
                                          color: const Color(0xFF1B224B).withOpacity(0.08),
                                          blurRadius: 30,
                                          offset: const Offset(0, 10),
                                        ),
                                      ],
                                    ),
                                    child: ClipRRect(
                                      borderRadius: BorderRadius.circular(110),
                                      child: Image.asset(
                                        'assets/images/athlete_hero.jpg',
                                        fit: BoxFit.cover,
                                        errorBuilder: (context, error, stackTrace) {
                                          return Container(
                                            color: AppTheme.surfaceWarm,
                                            child: const Center(
                                              child: Icon(
                                                Icons.directions_run_rounded,
                                                size: 90,
                                                color: AppTheme.primaryLight,
                                              ),
                                            ),
                                          );
                                        },
                                      ),
                                    ),
                                  ),
                                ),

                                // Floating Card 1: Top-Left (Dumbbell - Workout Engine)
                                Positioned(
                                  left: 8,
                                  top: (maxHeight * 0.22) + float1,
                                  child: const SquircleIconCard(
                                    icon: Icons.fitness_center_rounded,
                                    size: 58,
                                    iconSize: 26,
                                  ),
                                ),

                                // Floating Card 2: Top-Right (Line Chart - PRs & Growth)
                                Positioned(
                                  right: 8,
                                  top: (maxHeight * 0.20) + float2,
                                  child: const SquircleIconCard(
                                    icon: Icons.show_chart_rounded,
                                    size: 58,
                                    iconSize: 26,
                                  ),
                                ),

                                // Floating Card 3: Bottom-Left (Nutrition Bowl - Meal Vision)
                                Positioned(
                                  left: 14,
                                  bottom: (maxHeight * 0.22) + float3,
                                  child: const SquircleIconCard(
                                    icon: Icons.restaurant_rounded,
                                    size: 58,
                                    iconSize: 26,
                                  ),
                                ),

                                // Floating Card 4: Bottom-Right (Vision Scanner - CV Reticle)
                                Positioned(
                                  right: 14,
                                  bottom: (maxHeight * 0.20) + float4,
                                  child: const SquircleIconCard(
                                    icon: Icons.filter_center_focus_rounded,
                                    size: 58,
                                    iconSize: 26,
                                  ),
                                ),
                              ],
                            );
                          },
                        ),
                      ),
                    );
                  },
                ),
              ),

              // Bottom Action Section: Get Started Gradient Pill & Login Link
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Gradient Pill "Get Started ->" with touch micro-feedback
                    Container(
                      width: double.infinity,
                      height: 56,
                      decoration: BoxDecoration(
                        gradient: AppTheme.primaryGradient,
                        borderRadius: BorderRadius.circular(30),
                        boxShadow: AppTheme.buttonShadow,
                      ),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: () {
                            SoundService().playTapFeedback();
                            context.go('/auth');
                          },
                          borderRadius: BorderRadius.circular(30),
                          splashColor: Colors.white.withOpacity(0.15),
                          child: const Padding(
                            padding: EdgeInsets.symmetric(horizontal: 28),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  'Get Started',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 17,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 0.2,
                                  ),
                                ),
                                SizedBox(width: 12),
                                Icon(
                                  Icons.arrow_forward_rounded,
                                  color: Colors.white,
                                  size: 20,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 14),

                    // "Already have an account?" prompt
                    GestureDetector(
                      onTap: () {
                        SoundService().playTapFeedback();
                        context.go('/auth?mode=login');
                      },
                      child: const Padding(
                        padding: EdgeInsets.all(8.0),
                        child: Text(
                          'Already have an account?',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            letterSpacing: -0.2,
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 8),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
