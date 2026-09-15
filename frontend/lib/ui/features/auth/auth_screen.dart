import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme.dart';
import '../../../data/models/app_models.dart';
import '../../../data/services/api_service.dart';
import '../../widgets/glass_card.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool _isLogin = true;
  bool _isLoading = false;
  String? _errorMessage;

  final _emailCtrl = TextEditingController();
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();

  @override
  void dispose() {
    _emailCtrl.dispose();
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    _nameCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final api = ApiService();
    try {
      if (_isLogin) {
        final res = await api.login(
          usernameOrEmail: _emailCtrl.text.trim(),
          password: _passwordCtrl.text,
        );
        if (res['success'] == true) {
          if (mounted) context.go('/dashboard');
        } else {
          setState(() => _errorMessage = res['error']?.toString() ?? 'Login failed');
        }
      } else {
        final res = await api.register(
          email: _emailCtrl.text.trim(),
          username: _usernameCtrl.text.trim(),
          password: _passwordCtrl.text,
          fullName: _nameCtrl.text.trim(),
        );
        if (res['success'] == true) {
          if (mounted) context.go('/dashboard');
        } else {
          setState(() => _errorMessage = res['error']?.toString() ?? 'Registration failed');
        }
      }
    } catch (e) {
      setState(() => _errorMessage = 'Connection error: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _handleGuestBypass() {
    ApiService().setAuth(
      'guest_token',
      const User(id: 'default', email: 'guest@fitpath.ai', username: 'guest', fullName: 'Guest Athlete'),
    );
    context.go('/dashboard');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Logo / Header
                  Center(
                    child: Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withOpacity(0.15),
                        shape: BoxShape.circle,
                        border: Border.all(color: AppTheme.primary.withOpacity(0.4), width: 2),
                      ),
                      child: const Icon(Icons.fitness_center, color: AppTheme.primary, size: 42),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'FITPATH AI',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1.5,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Autonomous AI Coaching & Computer Vision',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 14, color: AppTheme.textSecondary),
                  ),
                  const SizedBox(height: 32),

                  // Auth Card
                  GlassCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Switch Tabs
                        Row(
                          children: [
                            Expanded(
                              child: TextButton(
                                onPressed: () => setState(() => _isLogin = true),
                                style: TextButton.styleFrom(
                                  foregroundColor: _isLogin ? AppTheme.primary : AppTheme.textSecondary,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(8),
                                    side: _isLogin
                                        ? const BorderSide(color: AppTheme.primary, width: 1.5)
                                        : BorderSide.none,
                                  ),
                                ),
                                child: const Text('Sign In', style: TextStyle(fontWeight: FontWeight.bold)),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: TextButton(
                                onPressed: () => setState(() => _isLogin = false),
                                style: TextButton.styleFrom(
                                  foregroundColor: !_isLogin ? AppTheme.primary : AppTheme.textSecondary,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(8),
                                    side: !_isLogin
                                        ? const BorderSide(color: AppTheme.primary, width: 1.5)
                                        : BorderSide.none,
                                  ),
                                ),
                                child: const Text('Register', style: TextStyle(fontWeight: FontWeight.bold)),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 20),

                        // Error Banner
                        if (_errorMessage != null) ...[
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: AppTheme.danger.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: AppTheme.danger.withOpacity(0.4)),
                            ),
                            child: Text(
                              _errorMessage!,
                              style: const TextStyle(color: AppTheme.danger, fontSize: 13),
                            ),
                          ),
                          const SizedBox(height: 16),
                        ],

                        // Form Inputs
                        if (!_isLogin) ...[
                          TextField(
                            controller: _nameCtrl,
                            decoration: const InputDecoration(
                              labelText: 'Full Name',
                              prefixIcon: Icon(Icons.badge, color: AppTheme.textSecondary),
                            ),
                          ),
                          const SizedBox(height: 14),
                          TextField(
                            controller: _usernameCtrl,
                            decoration: const InputDecoration(
                              labelText: 'Username',
                              prefixIcon: Icon(Icons.person, color: AppTheme.textSecondary),
                            ),
                          ),
                          const SizedBox(height: 14),
                        ],

                        TextField(
                          controller: _emailCtrl,
                          keyboardType: TextInputType.emailAddress,
                          decoration: InputDecoration(
                            labelText: _isLogin ? 'Email or Username' : 'Email',
                            prefixIcon: const Icon(Icons.email, color: AppTheme.textSecondary),
                          ),
                        ),
                        const SizedBox(height: 14),

                        TextField(
                          controller: _passwordCtrl,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'Password',
                            prefixIcon: Icon(Icons.lock, color: AppTheme.textSecondary),
                          ),
                        ),
                        const SizedBox(height: 24),

                        // Submit Button
                        ElevatedButton(
                          onPressed: _isLoading ? null : _handleSubmit,
                          child: _isLoading
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                                )
                              : Text(_isLogin ? 'Sign In' : 'Create Account'),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 20),

                  // Guest Bypass CTA
                  OutlinedButton.icon(
                    onPressed: _handleGuestBypass,
                    icon: const Icon(Icons.play_circle_outline, color: AppTheme.secondary),
                    label: const Text(
                      'Explore as Guest Athlete',
                      style: TextStyle(color: AppTheme.secondary, fontWeight: FontWeight.bold),
                    ),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      side: BorderSide(color: AppTheme.secondary.withOpacity(0.4)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
