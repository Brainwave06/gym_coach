import 'package:flutter_test/flutter_test.dart';
import 'package:fitpath_frontend/main.dart';
import 'package:fitpath_frontend/ui/features/onboarding/welcome_screen.dart';

void main() {
  testWidgets('FitPathApp loads WelcomeScreen with headline and Get Started', (WidgetTester tester) async {
    await tester.pumpWidget(const FitPathApp());
    // Pump frames for initial render (WelcomeScreen has continuous zero-g floating animation)
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    // Verify WelcomeScreen is rendered as initial screen
    expect(find.byType(WelcomeScreen), findsOneWidget);

    // Verify Brand Logo and Headlines from user reference design
    expect(find.text('FitPath'), findsOneWidget);
    expect(find.text('Smarter Training.\nBetter You.'), findsOneWidget);
    expect(find.text('Get Started'), findsOneWidget);
    expect(find.text('Already have an account?'), findsOneWidget);
  });
}
