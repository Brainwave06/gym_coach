import 'package:flutter_test/flutter_test.dart';
import 'package:fitpath_frontend/main.dart';

void main() {
  testWidgets('FitPathApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const FitPathApp());
    expect(find.byType(FitPathApp), findsOneWidget);
  });
}
