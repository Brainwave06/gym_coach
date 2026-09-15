import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme.dart';
import '../../../data/models/app_models.dart';
import '../../../data/services/api_service.dart';
import '../../widgets/fitpath_logo.dart';
import '../../widgets/glass_card.dart';

class AuthScreen extends StatefulWidget {
  final bool initialIsLogin;
  const AuthScreen({super.key, this.initialIsLogin = true});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  late bool _isLogin;
  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;

  final _emailCtrl = TextEditingController();
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _isLogin = widget.initialIsLogin;
  }

  @override
  void dispose() {
    _emailCtrl.dispose();
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    _nameCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    final emailOrUser = _emailCtrl.text.trim();
    final password = _passwordCtrl.text;

    if (emailOrUser.isEmpty) {
      setState(() => _errorMessage = _isLogin ? 'Please enter your email or username.' : 'Please enter your email address.');
      return;
    }

    if (!_isLogin && _usernameCtrl.text.trim().isEmpty) {
      setState(() => _errorMessage = 'Please choose a username.');
      return;
    }

    if (password.length < 6) {
      setState(() => _errorMessage = 'Password must be at least 6 characters.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final api = ApiService();
    try {
      if (_isLogin) {
        final res = await api.login(
          usernameOrEmail: emailOrUser,
          password: password,
        );
        if (res['success'] == true) {
          if (mounted) context.go('/dashboard');
        } else {
          setState(() => _errorMessage = res['error']?.toString() ?? 'Invalid credentials');
        }
      } else {
        final res = await api.register(
          email: emailOrUser,
          username: _usernameCtrl.text.trim(),
          password: password,
          fullName: _nameCtrl.text.trim().isEmpty ? null : _nameCtrl.text.trim(),
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

  Future<void> _handleDemoAthleteLogin() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final res = await ApiService().loginAsDemoAthlete();
      if (res['success'] == true) {
        if (mounted) context.go('/dashboard');
      } else {
        setState(() => _errorMessage = res['error']?.toString() ?? 'Demo athlete login failed');
      }
    } catch (_) {
      _handleGuestBypass();
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _handleGuestBypass() {
    ApiService().setAuth(
      'guest_token',
      const User(
        id: 'default',
        email: 'guest@fitpath.ai',
        username: 'guest',
        fullName: 'Guest Athlete',
      ),
    );
    context.go('/dashboard');
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
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Brand Logo
                    const Center(
                      child: FitPathLogo(
                        size: 48,
                        showText: true,
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Smarter Training. Better You.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 28),

                    // Luxury Card Container
                    GlassCard(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // Segmented Pill Switch
                          Container(
                            height: 48,
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceWarm,
                              borderRadius: BorderRadius.circular(24),
                              border: Border.all(
                                color: AppTheme.surfaceWarmBorder.withOpacity(0.5),
                              ),
                            ),
                            child: Row(
                              children: [
                                Expanded(
                                  child: GestureDetector(
                                    onTap: () => setState(() => _isLogin = true),
                                    child: Container(
                                      decoration: BoxDecoration(
                                        color: _isLogin ? AppTheme.primary : Colors.transparent,
                                        borderRadius: BorderRadius.circular(20),
                                        boxShadow: _isLogin
                                            ? [
                                                BoxShadow(
                                                  color: AppTheme.primary.withOpacity(0.2),
                                                  blurRadius: 8,
                                                  offset: const Offset(0, 2),
                                                ),
                                              ]
                                            : null,
                                      ),
                                      alignment: Alignment.center,
                                      child: Text(
                                        'Sign In',
                                        style: TextStyle(
                                          color: _isLogin ? Colors.white : AppTheme.textSecondary,
                                          fontWeight: FontWeight.w700,
                                          fontSize: 14,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                                Expanded(
                                  child: GestureDetector(
                                    onTap: () => setState(() => _isLogin = false),
                                    child: Container(
                                      decoration: BoxDecoration(
                                        color: !_isLogin ? AppTheme.primary : Colors.transparent,
                                        borderRadius: BorderRadius.circular(20),
                                        boxShadow: !_isLogin
                                            ? [
                                                BoxShadow(
                                                  color: AppTheme.primary.withOpacity(0.2),
                                                  blurRadius: 8,
                                                  offset: const Offset(0, 2),
                                                ),
                                              ]
                                            : null,
                                      ),
                                      alignment: Alignment.center,
                                      child: Text(
                                        'Register',
                                        style: TextStyle(
                                          color: !_isLogin ? Colors.white : AppTheme.textSecondary,
                                          fontWeight: FontWeight.w700,
                                          fontSize: 14,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 24),

                          // Error message banner
                          if (_errorMessage != null) ...[
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                              decoration: BoxDecoration(
                                color: AppTheme.accentCoral.withOpacity(0.08),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(
                                  color: AppTheme.accentCoral.withOpacity(0.3),
                                ),
                              ),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.error_outline_rounded,
                                    color: AppTheme.accentCoral,
                                    size: 18,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      _errorMessage!,
                                      style: const TextStyle(
                                        color: AppTheme.accentCoral,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 16),
                          ],

                          // Inputs
                          if (!_isLogin) ...[
                            TextField(
                              controller: _nameCtrl,
                              style: const TextStyle(color: AppTheme.textPrimary),
                              decoration: const InputDecoration(
                                labelText: 'Full Name',
                                prefixIcon: Icon(Icons.badge_outlined, color: AppTheme.textSecondary),
                              ),
                            ),
                            const SizedBox(height: 14),
                            TextField(
                              controller: _usernameCtrl,
                              style: const TextStyle(color: AppTheme.textPrimary),
                              decoration: const InputDecoration(
                                labelText: 'Username',
                                prefixIcon: Icon(Icons.person_outline, color: AppTheme.textSecondary),
                              ),
                            ),
                            const SizedBox(height: 14),
                          ],

                          TextField(
                            controller: _emailCtrl,
                            keyboardType: TextInputType.emailAddress,
                            style: const TextStyle(color: AppTheme.textPrimary),
                            decoration: InputDecoration(
                              labelText: _isLogin ? 'Email or Username' : 'Email Address',
                              prefixIcon: const Icon(Icons.email_outlined, color: AppTheme.textSecondary),
                            ),
                          ),
                          const SizedBox(height: 14),

                          TextField(
                            controller: _passwordCtrl,
                            obscureText: _obscurePassword,
                            style: const TextStyle(color: AppTheme.textPrimary),
                            decoration: InputDecoration(
                              labelText: 'Password',
                              prefixIcon: const Icon(Icons.lock_outline, color: AppTheme.textSecondary),
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                                  color: AppTheme.textSecondary,
                                  size: 20,
                                ),
                                tooltip: _obscurePassword ? 'Show password' : 'Hide password',
                                onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                              ),
                            ),
                          ),
                          const SizedBox(height: 24),

                          // Gradient Pill Submit Button
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
                                onTap: _isLoading ? null : _handleSubmit,
                                borderRadius: BorderRadius.circular(30),
                                splashColor: Colors.white.withOpacity(0.15),
                                child: Center(
                                  child: _isLoading
                                      ? const SizedBox(
                                          width: 22,
                                          height: 22,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2.2,
                                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                          ),
                                        )
                                      : Row(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: [
                                            Text(
                                              _isLogin ? 'Sign In' : 'Create Account',
                                              style: const TextStyle(
                                                color: Colors.white,
                                                fontSize: 16,
                                                fontWeight: FontWeight.w700,
                                                letterSpacing: 0.2,
                                              ),
                                            ),
                                            const SizedBox(width: 8),
                                            const Icon(
                                              Icons.arrow_forward_rounded,
                                              color: Colors.white,
                                              size: 18,
                                            ),
                                          ],
                                        ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 18),

                    // 1-Tap Demo Athlete Button
                    Container(
                      height: 50,
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFF9E6),
                        borderRadius: BorderRadius.circular(26),
                        border: Border.all(
                          color: const Color(0xFFFFD54F).withOpacity(0.8),
                          width: 1.5,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFFFFD54F).withOpacity(0.15),
                            blurRadius: 10,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: _isLoading ? null : _handleDemoAthleteLogin,
                          borderRadius: BorderRadius.circular(26),
                          child: const Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.bolt_rounded,
                                color: Color(0xFFD97706),
                                size: 22,
                              ),
                              SizedBox(width: 8),
                              Text(
                                '⚡ 1-Tap Login as Demo Athlete',
                                style: TextStyle(
                                  color: Color(0xFF92400E),
                                  fontWeight: FontWeight.w800,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 12),

                    // Guest Athlete Text Button
                    TextButton.icon(
                      onPressed: _handleGuestBypass,
                      icon: const Icon(Icons.explore_outlined, size: 16, color: AppTheme.textSecondary),
                      label: const Text(
                        'Continue as Guest Athlete (Skip Login)',
                        style: TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
