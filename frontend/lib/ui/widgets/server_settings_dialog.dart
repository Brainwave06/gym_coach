import 'package:flutter/material.dart';
import '../../../core/constants.dart';
import '../../../core/theme.dart';
import '../../../data/services/api_service.dart';

class ServerSettingsDialog extends StatefulWidget {
  const ServerSettingsDialog({super.key});

  static Future<void> show(BuildContext context) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => const ServerSettingsDialog(),
    );
  }

  @override
  State<ServerSettingsDialog> createState() => _ServerSettingsDialogState();
}

class _ServerSettingsDialogState extends State<ServerSettingsDialog> {
  late final TextEditingController _controller;
  bool _isTesting = false;
  bool? _testSuccess;
  String? _testMessage;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: AppConstants.apiBaseUrl);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    final url = _controller.text.trim();
    if (url.isEmpty) return;

    setState(() {
      _isTesting = true;
      _testSuccess = null;
      _testMessage = null;
    });

    final res = await ApiService().testConnection(url);

    if (mounted) {
      setState(() {
        _isTesting = false;
        _testSuccess = res['success'] as bool? ?? false;
        _testMessage = res['message'] as String? ?? '';
      });
    }
  }

  Future<void> _saveAndApply() async {
    final url = _controller.text.trim();
    if (url.isNotEmpty) {
      await AppConstants.setCustomBaseUrl(url);
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: const Color(0xFF1B2342),
            content: Row(
              children: [
                const Icon(Icons.check_circle_rounded, color: AppTheme.accentGreen, size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Backend configured: $url',
                    style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      padding: EdgeInsets.fromLTRB(24, 20, 24, 24 + bottomInset),
      decoration: const BoxDecoration(
        color: Color(0xFF11162A),
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        boxShadow: [
          BoxShadow(
            color: Colors.black54,
            blurRadius: 30,
            offset: Offset(0, -5),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Drag handle
          Center(
            child: Container(
              width: 44,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 18),

          // Title Row
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF3B487A), Color(0xFF1E2648)],
                  ),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(Icons.dns_rounded, color: AppTheme.accentGold, size: 22),
              ),
              const SizedBox(width: 14),
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Backend Server Target',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Connect your phone to the FitPath engine',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.white54,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Presets Title
          const Text(
            'QUICK CONNECT PRESETS',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.1,
              color: Colors.white38,
            ),
          ),
          const SizedBox(height: 10),

          // Preset Chips
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _buildPresetChip(
                label: '🌐 Live Cloud Tunnel',
                sublabel: 'Works anywhere (4G/5G/WiFi)',
                url: AppConstants.defaultTunnelUrl,
              ),
              _buildPresetChip(
                label: '📶 Home Wi-Fi',
                sublabel: '192.168.1.4:8000',
                url: AppConstants.defaultWifiUrl,
              ),
              _buildPresetChip(
                label: '💻 USB / ADB Reverse',
                sublabel: '127.0.0.1:8000',
                url: AppConstants.defaultLocalUrl,
              ),
            ],
          ),
          const SizedBox(height: 18),

          // Custom Input Field
          const Text(
            'CUSTOM SERVER URL',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.1,
              color: Colors.white38,
            ),
          ),
          const SizedBox(height: 8),

          Container(
            decoration: BoxDecoration(
              color: const Color(0xFF1A213B),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: _testSuccess == true
                    ? AppTheme.accentGreen.withOpacity(0.5)
                    : _testSuccess == false
                        ? AppTheme.accentCoral.withOpacity(0.5)
                        : Colors.white.withOpacity(0.12),
              ),
            ),
            child: TextField(
              controller: _controller,
              style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
              decoration: InputDecoration(
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                border: InputBorder.none,
                hintText: 'https://your-backend.onrender.com',
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.3), fontSize: 13),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.clear, color: Colors.white38, size: 18),
                  onPressed: () => _controller.clear(),
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Live Test Status Feedback
          if (_testMessage != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: _testSuccess == true
                    ? AppTheme.accentGreen.withOpacity(0.15)
                    : AppTheme.accentCoral.withOpacity(0.15),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: _testSuccess == true
                      ? AppTheme.accentGreen.withOpacity(0.4)
                      : AppTheme.accentCoral.withOpacity(0.4),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    _testSuccess == true ? Icons.check_circle_rounded : Icons.error_outline_rounded,
                    size: 16,
                    color: _testSuccess == true ? AppTheme.accentGreen : AppTheme.accentCoral,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _testMessage!,
                      style: TextStyle(
                        color: _testSuccess == true ? AppTheme.accentGreen : AppTheme.accentCoral,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),

          // Action Buttons
          Row(
            children: [
              // Test Button
              Expanded(
                flex: 2,
                child: OutlinedButton(
                  onPressed: _isTesting ? null : _testConnection,
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    side: BorderSide(color: Colors.white.withOpacity(0.25)),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  child: _isTesting
                      ? const SizedBox(
                          height: 18,
                          width: 18,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.wifi_tethering_rounded, size: 16, color: Colors.white),
                            SizedBox(width: 6),
                            Text(
                              'Test Ping',
                              style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w700,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                ),
              ),
              const SizedBox(width: 10),

              // Save & Apply Button
              Expanded(
                flex: 3,
                child: ElevatedButton(
                  onPressed: _saveAndApply,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    backgroundColor: AppTheme.accentGold,
                    foregroundColor: const Color(0xFF0F1424),
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.save_rounded, size: 17),
                      SizedBox(width: 6),
                      Text(
                        'Save & Connect',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPresetChip({
    required String label,
    required String sublabel,
    required String url,
  }) {
    final isSelected = _controller.text.trim() == url.trim();

    return InkWell(
      onTap: () {
        setState(() {
          _controller.text = url;
          _testSuccess = null;
          _testMessage = null;
        });
      },
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.accentGold.withOpacity(0.18) : const Color(0xFF192038),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? AppTheme.accentGold : Colors.white.withOpacity(0.12),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: TextStyle(
                color: isSelected ? AppTheme.accentGold : Colors.white,
                fontWeight: FontWeight.w700,
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              sublabel,
              style: TextStyle(
                color: isSelected ? AppTheme.accentGold.withOpacity(0.7) : Colors.white38,
                fontSize: 10,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
