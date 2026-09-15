class User {
  final String id;
  final String email;
  final String username;
  final String fullName;

  const User({
    required this.id,
    required this.email,
    required this.username,
    required this.fullName,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? json['username']?.toString() ?? 'Athlete',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'email': email,
    'username': username,
    'full_name': fullName,
  };
}

class Biometrics {
  final double bmi;
  final String bmiCategory;
  final int bmrKcal;
  final int tdeeKcal;
  final double proteinTargetG;
  final double carbTargetG;
  final double fatTargetG;
  final int hydrationTargetMl;

  const Biometrics({
    required this.bmi,
    required this.bmiCategory,
    required this.bmrKcal,
    required this.tdeeKcal,
    required this.proteinTargetG,
    required this.carbTargetG,
    required this.fatTargetG,
    required this.hydrationTargetMl,
  });

  factory Biometrics.fromJson(Map<String, dynamic> json) {
    return Biometrics(
      bmi: (json['bmi'] as num?)?.toDouble() ?? 22.0,
      bmiCategory: json['bmi_category']?.toString() ?? 'Normal',
      bmrKcal: (json['bmr_kcal'] as num?)?.toInt() ?? 1700,
      tdeeKcal: (json['tdee_kcal'] as num?)?.toInt() ?? 2200,
      proteinTargetG: (json['protein_target_g'] as num?)?.toDouble() ?? 140.0,
      carbTargetG: (json['carb_target_g'] as num?)?.toDouble() ?? 220.0,
      fatTargetG: (json['fat_target_g'] as num?)?.toDouble() ?? 60.0,
      hydrationTargetMl: (json['hydration_target_ml'] as num?)?.toInt() ?? 2500,
    );
  }
}

class AthleteProfile {
  final String name;
  final double heightCm;
  final double weightKg;
  final int age;
  final String gender;
  final String goal;
  final String fitnessLevel;
  final String dietaryPreferences;
  final List<String> injuries;
  final Biometrics? biometrics;

  const AthleteProfile({
    required this.name,
    required this.heightCm,
    required this.weightKg,
    required this.age,
    required this.gender,
    required this.goal,
    required this.fitnessLevel,
    required this.dietaryPreferences,
    required this.injuries,
    this.biometrics,
  });

  factory AthleteProfile.fromJson(Map<String, dynamic> json, {Biometrics? biometrics}) {
    return AthleteProfile(
      name: json['name']?.toString() ?? 'Athlete',
      heightCm: (json['height_cm'] as num?)?.toDouble() ?? 175.0,
      weightKg: (json['weight_kg'] as num?)?.toDouble() ?? 70.0,
      age: (json['age'] as num?)?.toInt() ?? 25,
      gender: json['gender']?.toString() ?? 'male',
      goal: json['goal']?.toString() ?? 'health',
      fitnessLevel: json['fitness_level']?.toString() ?? 'intermediate',
      dietaryPreferences: json['dietary_preferences']?.toString() ?? 'none',
      injuries: (json['injuries'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      biometrics: biometrics,
    );
  }
}

class MealItem {
  final String name;
  final int portionG;
  final int calories;
  final double proteinG;
  final double carbsG;
  final double fatG;

  const MealItem({
    required this.name,
    required this.portionG,
    required this.calories,
    required this.proteinG,
    required this.carbsG,
    required this.fatG,
  });

  factory MealItem.fromJson(Map<String, dynamic> json) {
    return MealItem(
      name: json['name']?.toString() ?? 'Item',
      portionG: (json['portion_g'] as num?)?.toInt() ?? 100,
      calories: (json['calories'] as num?)?.toInt() ?? 0,
      proteinG: (json['protein_g'] as num?)?.toDouble() ?? 0.0,
      carbsG: (json['carbs_g'] as num?)?.toDouble() ?? 0.0,
      fatG: (json['fat_g'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class MealAnalysis {
  final String mealName;
  final List<MealItem> items;
  final int totalCalories;
  final double totalProteinG;
  final double totalCarbsG;
  final double totalFatG;
  final String coachFeedback;
  final List<String> suggestions;
  final double proteinCoveragePct;

  const MealAnalysis({
    required this.mealName,
    required this.items,
    required this.totalCalories,
    required this.totalProteinG,
    required this.totalCarbsG,
    required this.totalFatG,
    required this.coachFeedback,
    required this.suggestions,
    required this.proteinCoveragePct,
  });

  factory MealAnalysis.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List<dynamic>? ?? [];
    final itemsList = rawItems.map((i) => MealItem.fromJson(i as Map<String, dynamic>)).toList();
    final targetComp = json['target_comparison'] as Map<String, dynamic>?;
    final coverage = (targetComp?['meal_protein_coverage_pct'] as num?)?.toDouble() ?? 0.0;

    return MealAnalysis(
      mealName: json['meal_name']?.toString() ?? 'Plate Analysis',
      items: itemsList,
      totalCalories: (json['total_calories'] as num?)?.toInt() ?? 0,
      totalProteinG: (json['total_protein_g'] as num?)?.toDouble() ?? 0.0,
      totalCarbsG: (json['total_carbs_g'] as num?)?.toDouble() ?? 0.0,
      totalFatG: (json['total_fat_g'] as num?)?.toDouble() ?? 0.0,
      coachFeedback: json['coach_feedback']?.toString() ?? 'Solid plate composition.',
      suggestions: (json['suggestions'] as List<dynamic>?)?.map((s) => s.toString()).toList() ?? [],
      proteinCoveragePct: coverage,
    );
  }
}
