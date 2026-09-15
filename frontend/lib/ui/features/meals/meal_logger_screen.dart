import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../../../core/theme.dart';
import '../../../data/models/app_models.dart';
import '../../../data/services/api_service.dart';
import '../../widgets/glass_card.dart';
import '../../widgets/squircle_icon_card.dart';

class MealLoggerScreen extends StatefulWidget {
  const MealLoggerScreen({super.key});

  @override
  State<MealLoggerScreen> createState() => _MealLoggerScreenState();
}

class _MealLoggerScreenState extends State<MealLoggerScreen> {
  final ImagePicker _picker = ImagePicker();
  Uint8List? _selectedImageBytes;
  String? _selectedFilename;
  final TextEditingController _notesCtrl = TextEditingController();

  bool _isAnalyzing = false;
  MealAnalysis? _analysisResult;
  String? _error;

  @override
  void dispose() {
    _notesCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? file = await _picker.pickImage(
        source: source,
        maxWidth: 1200,
        maxHeight: 1200,
        imageQuality: 85,
      );
      if (file != null) {
        final bytes = await file.readAsBytes();
        setState(() {
          _selectedImageBytes = bytes;
          _selectedFilename = file.name;
          _analysisResult = null;
          _error = null;
        });
      }
    } catch (e) {
      setState(() => _error = 'Could not pick image: $e');
    }
  }

  Future<void> _analyzePlate() async {
    if (_selectedImageBytes == null) return;

    setState(() {
      _isAnalyzing = true;
      _error = null;
    });

    try {
      final result = await ApiService().analyzeMeal(
        imageBytes: _selectedImageBytes!,
        filename: _selectedFilename ?? 'plate.jpg',
        notes: _notesCtrl.text.trim(),
      );
      setState(() => _analysisResult = result);
    } catch (e) {
      setState(() => _error = 'Vision analysis error: $e');
    } finally {
      if (mounted) setState(() => _isAnalyzing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text(
          'Meal Vision Logger',
          style: TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 20,
            fontWeight: FontWeight.w800,
            letterSpacing: -0.4,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Intro Card with Squircle Icon
            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Row(
                children: [
                  const SquircleIconCard(
                    icon: Icons.filter_center_focus_rounded,
                    size: 48,
                    iconSize: 24,
                  ),
                  const SizedBox(width: 14),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Plate Vision AI Scanner',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 15,
                            color: AppTheme.textPrimary,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Snap your plate to estimate weights, calories, and macros against your daily targets.',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                            height: 1.35,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Image Picker / Preview
            if (_selectedImageBytes != null)
              Stack(
                children: [
                  Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: AppTheme.softShadow,
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(24),
                      child: Image.memory(
                        _selectedImageBytes!,
                        height: 260,
                        width: double.infinity,
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),
                  Positioned(
                    top: 12,
                    right: 12,
                    child: CircleAvatar(
                      backgroundColor: Colors.black.withOpacity(0.65),
                      radius: 18,
                      child: IconButton(
                        icon: const Icon(Icons.close_rounded, color: Colors.white, size: 18),
                        onPressed: () => setState(() {
                          _selectedImageBytes = null;
                          _analysisResult = null;
                        }),
                      ),
                    ),
                  ),
                ],
              )
            else
              Row(
                children: [
                  Expanded(
                    child: GestureDetector(
                      onTap: () => _pickImage(ImageSource.camera),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 22),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceWarm,
                          borderRadius: BorderRadius.circular(22),
                          border: Border.all(
                            color: AppTheme.surfaceWarmBorder.withOpacity(0.7),
                          ),
                        ),
                        child: const Column(
                          children: [
                            Icon(
                              Icons.camera_alt_rounded,
                              color: AppTheme.primary,
                              size: 28,
                            ),
                            SizedBox(height: 8),
                            Text(
                              'Take Photo',
                              style: TextStyle(
                                color: AppTheme.primary,
                                fontWeight: FontWeight.w700,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: GestureDetector(
                      onTap: () => _pickImage(ImageSource.gallery),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 22),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceWarm,
                          borderRadius: BorderRadius.circular(22),
                          border: Border.all(
                            color: AppTheme.surfaceWarmBorder.withOpacity(0.7),
                          ),
                        ),
                        child: const Column(
                          children: [
                            Icon(
                              Icons.photo_library_rounded,
                              color: AppTheme.primaryLight,
                              size: 28,
                            ),
                            SizedBox(height: 8),
                            Text(
                              'From Gallery',
                              style: TextStyle(
                                color: AppTheme.primary,
                                fontWeight: FontWeight.w700,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),

            if (_selectedImageBytes != null) ...[
              const SizedBox(height: 18),
              TextField(
                controller: _notesCtrl,
                style: const TextStyle(color: AppTheme.textPrimary),
                decoration: const InputDecoration(
                  labelText: 'Optional Meal Notes (e.g. 200g grilled salmon with rice)',
                  prefixIcon: Icon(Icons.notes_rounded, color: AppTheme.textSecondary),
                ),
              ),
              const SizedBox(height: 18),
              // Gradient Pill Analyze Button
              Container(
                height: 54,
                decoration: BoxDecoration(
                  gradient: AppTheme.primaryGradient,
                  borderRadius: BorderRadius.circular(30),
                  boxShadow: AppTheme.buttonShadow,
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: _isAnalyzing ? null : _analyzePlate,
                    borderRadius: BorderRadius.circular(30),
                    splashColor: Colors.white.withOpacity(0.15),
                    child: Center(
                      child: _isAnalyzing
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.2,
                                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                              ),
                            )
                          : const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.auto_awesome_rounded, color: Colors.white, size: 20),
                                SizedBox(width: 10),
                                Text(
                                  'Analyze Plate with Vision AI',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 16,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 0.2,
                                  ),
                                ),
                              ],
                            ),
                    ),
                  ),
                ),
              ),
            ],

            if (_error != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.accentCoral.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppTheme.accentCoral.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline_rounded, color: AppTheme.accentCoral, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _error!,
                        style: const TextStyle(color: AppTheme.accentCoral, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Analysis Results Presentation
            if (_analysisResult != null) ...[
              const SizedBox(height: 24),
              Text(
                _analysisResult!.mealName.toUpperCase(),
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 18,
                  color: AppTheme.textPrimary,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 12),

              // Macro Badges Row
              Row(
                children: [
                  Expanded(
                    child: _buildMacroCard('Calories', '${_analysisResult!.totalCalories}', 'kcal', const Color(0xFFE65100)),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _buildMacroCard('Protein', '${_analysisResult!.totalProteinG.toInt()}', 'g', AppTheme.primary),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _buildMacroCard('Carbs', '${_analysisResult!.totalCarbsG.toInt()}', 'g', AppTheme.primaryLight),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _buildMacroCard('Fat', '${_analysisResult!.totalFatG.toInt()}', 'g', AppTheme.accentGold),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Identified Food Items
              GlassCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'IDENTIFIED INGREDIENTS',
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                        color: AppTheme.textSecondary,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: 12),
                    ..._analysisResult!.items.map(
                      (item) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Row(
                              children: [
                                Container(
                                  width: 8,
                                  height: 8,
                                  decoration: const BoxDecoration(
                                    color: AppTheme.primary,
                                    shape: BoxShape.circle,
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Text(
                                  item.name,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 14,
                                    color: AppTheme.textPrimary,
                                  ),
                                ),
                              ],
                            ),
                            Text(
                              '${item.portionG}g • ${item.calories} kcal',
                              style: const TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Sports Nutritionist Coach Feedback Card
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceWarm,
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(
                    color: AppTheme.surfaceWarmBorder.withOpacity(0.8),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(
                          Icons.sports_score_rounded,
                          color: AppTheme.primary,
                          size: 22,
                        ),
                        SizedBox(width: 8),
                        Text(
                          'COACH NUTRITION FEEDBACK',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            color: AppTheme.primary,
                            fontSize: 12,
                            letterSpacing: 0.8,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      _analysisResult!.coachFeedback,
                      style: const TextStyle(
                        fontSize: 13.5,
                        height: 1.45,
                        color: AppTheme.textPrimary,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildMacroCard(String label, String value, String unit, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.cardBorder),
        boxShadow: AppTheme.softShadow,
      ),
      child: Column(
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 11,
              color: AppTheme.textSecondary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                value,
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                  fontSize: 18,
                  color: color,
                ),
              ),
              const SizedBox(width: 2),
              Text(
                unit,
                style: TextStyle(
                  fontSize: 10,
                  color: color.withOpacity(0.8),
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
