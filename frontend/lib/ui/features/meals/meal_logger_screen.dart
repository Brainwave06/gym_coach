import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../../../core/theme.dart';
import '../../../data/models/app_models.dart';
import '../../../data/services/api_service.dart';
import '../../widgets/glass_card.dart';

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
      final XFile? file = await _picker.pickImage(source: source, maxWidth: 1200, maxHeight: 1200, imageQuality: 85);
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
      appBar: AppBar(
        title: const Text('VISUAL FOOD LOGGER'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Instructions / Info Card
            GlassCard(
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.secondary.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.camera_alt, color: AppTheme.secondary, size: 28),
                  ),
                  const SizedBox(width: 14),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Multimodal Plate Vision AI', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                        SizedBox(height: 4),
                        Text(
                          'Snap your meal to estimate portion weights, calories, and macros against your daily targets.',
                          style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Image Picker / Preview Box
            if (_selectedImageBytes != null)
              Stack(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(20),
                    child: Image.memory(
                      _selectedImageBytes!,
                      height: 260,
                      width: double.infinity,
                      fit: BoxFit.cover,
                    ),
                  ),
                  Positioned(
                    top: 10,
                    right: 10,
                    child: CircleAvatar(
                      backgroundColor: Colors.black.withOpacity(0.7),
                      child: IconButton(
                        icon: const Icon(Icons.close, color: Colors.white, size: 18),
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
                    child: OutlinedButton.icon(
                      onPressed: () => _pickImage(ImageSource.camera),
                      icon: const Icon(Icons.camera_alt, color: AppTheme.primary),
                      label: const Text('Take Photo', style: TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold)),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 20),
                        side: BorderSide(color: AppTheme.primary.withOpacity(0.4)),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _pickImage(ImageSource.gallery),
                      icon: const Icon(Icons.photo_library, color: AppTheme.secondary),
                      label: const Text('From Gallery', style: TextStyle(color: AppTheme.secondary, fontWeight: FontWeight.bold)),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 20),
                        side: BorderSide(color: AppTheme.secondary.withOpacity(0.4)),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      ),
                    ),
                  ),
                ],
              ),

            if (_selectedImageBytes != null) ...[
              const SizedBox(height: 16),
              TextField(
                controller: _notesCtrl,
                decoration: const InputDecoration(
                  labelText: 'Optional Meal Notes (e.g. 200g grilled chicken breast)',
                  prefixIcon: Icon(Icons.notes, color: AppTheme.textSecondary),
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _isAnalyzing ? null : _analyzePlate,
                icon: _isAnalyzing
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                    : const Icon(Icons.auto_awesome, color: Colors.black),
                label: Text(_isAnalyzing ? 'Qwen-VL Analyzing Plate...' : 'Analyze Plate with Vision AI'),
              ),
            ],

            if (_error != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.danger.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.danger.withOpacity(0.4)),
                ),
                child: Text(_error!, style: const TextStyle(color: AppTheme.danger, fontSize: 13)),
              ),
            ],

            // Analysis Result Presentation
            if (_analysisResult != null) ...[
              const SizedBox(height: 24),
              Text(
                _analysisResult!.mealName.toUpperCase(),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: AppTheme.primary),
              ),
              const SizedBox(height: 12),

              // Macro Badges
              Row(
                children: [
                  Expanded(child: _buildMacroCard('Calories', '${_analysisResult!.totalCalories}', 'kcal', Colors.orange)),
                  const SizedBox(width: 8),
                  Expanded(child: _buildMacroCard('Protein', '${_analysisResult!.totalProteinG.toInt()}', 'g', AppTheme.primary)),
                  const SizedBox(width: 8),
                  Expanded(child: _buildMacroCard('Carbs', '${_analysisResult!.totalCarbsG.toInt()}', 'g', AppTheme.secondary)),
                  const SizedBox(width: 8),
                  Expanded(child: _buildMacroCard('Fat', '${_analysisResult!.totalFatG.toInt()}', 'g', Colors.pinkAccent)),
                ],
              ),
              const SizedBox(height: 16),

              // Identified Ingredients List
              GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('IDENTIFIED ITEMS', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.textSecondary)),
                    const SizedBox(height: 10),
                    ..._analysisResult!.items.map(
                      (item) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(item.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                            Text('${item.portionG}g • ${item.calories} kcal', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Coach Feedback Card
              GlassCard(
                borderColor: AppTheme.primary.withOpacity(0.3),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.sports_score, color: AppTheme.primary, size: 20),
                        SizedBox(width: 8),
                        Text('COACH FEEDBACK', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primary, fontSize: 13)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _analysisResult!.coachFeedback,
                      style: const TextStyle(fontSize: 13.5, height: 1.4),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildMacroCard(String label, String value, String unit, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
          const SizedBox(height: 4),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(value, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: color)),
              const SizedBox(width: 2),
              Text(unit, style: TextStyle(fontSize: 10, color: color.withOpacity(0.8))),
            ],
          ),
        ],
      ),
    );
  }
}
