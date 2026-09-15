import 'package:flutter/material.dart';
import '../../../core/theme.dart';
import '../../../data/services/api_service.dart';
import '../../widgets/squircle_icon_card.dart';

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  const ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
  });
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<ChatMessage> _messages = [];
  final TextEditingController _textCtrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  bool _isSending = false;

  final List<String> _quickPrompts = [
    'How is my daily protein intake?',
    'Fix my knee cave in squats',
    'What should I eat post-workout?',
    'Review my recent strength PRs',
  ];

  @override
  void initState() {
    super.initState();
    _messages.add(
      ChatMessage(
        text: "Hey! I'm your FitPath Coach. I'm connected to your computer-vision training sessions and nutrition logs. How can I help you crush your goals today?",
        isUser: false,
        timestamp: DateTime.now(),
      ),
    );
  }

  @override
  void dispose() {
    _textCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage([String? customText]) async {
    final text = customText ?? _textCtrl.text.trim();
    if (text.isEmpty || _isSending) return;

    if (customText == null) _textCtrl.clear();

    setState(() {
      _messages.add(ChatMessage(text: text, isUser: true, timestamp: DateTime.now()));
      _isSending = true;
    });
    _scrollToBottom();

    try {
      final history = _messages.map((m) => {'role': m.isUser ? 'user' : 'assistant', 'content': m.text}).toList();
      final reply = await ApiService().sendChatMessage(text, history: history);
      if (mounted) {
        setState(() {
          _messages.add(ChatMessage(text: reply, isUser: false, timestamp: DateTime.now()));
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages.add(ChatMessage(text: 'Error contacting coach: $e', isUser: false, timestamp: DateTime.now()));
        });
      }
    } finally {
      if (mounted) setState(() => _isSending = false);
      _scrollToBottom();
    }
  }

  Future<void> _loadDebrief() async {
    setState(() => _isSending = true);
    try {
      final debrief = await ApiService().getPostWorkoutDebrief();
      if (mounted) {
        setState(() {
          _messages.add(ChatMessage(text: "📊 POST-WORKOUT COACH DEBRIEF:\n\n$debrief", isUser: false, timestamp: DateTime.now()));
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages.add(ChatMessage(text: "Could not load debrief: $e", isUser: false, timestamp: DateTime.now()));
        });
      }
    } finally {
      if (mounted) setState(() => _isSending = false);
      _scrollToBottom();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        titleSpacing: 16,
        title: const Row(
          children: [
            SquircleIconCard(
              icon: Icons.auto_awesome_rounded,
              size: 38,
              iconSize: 20,
              backgroundColor: AppTheme.surfaceWarm,
              iconColor: AppTheme.primary,
            ),
            SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'FitPath Coach',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.textPrimary,
                    letterSpacing: -0.4,
                  ),
                ),
                Text(
                  'Powered by Qwen & Sports RAG',
                  style: TextStyle(
                    fontSize: 11,
                    color: AppTheme.textSecondary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 14),
            child: GestureDetector(
              onTap: _isSending ? null : _loadDebrief,
              child: Container(
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
                      Icons.assessment_outlined,
                      size: 16,
                      color: AppTheme.primary,
                    ),
                    SizedBox(width: 6),
                    Text(
                      'Debrief',
                      style: TextStyle(
                        color: AppTheme.primary,
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // Messages List
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                return Align(
                  alignment: msg.isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 14),
                    constraints: BoxConstraints(
                      maxWidth: MediaQuery.of(context).size.width * 0.82,
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                    decoration: BoxDecoration(
                      gradient: msg.isUser ? AppTheme.primaryGradient : null,
                      color: msg.isUser ? null : AppTheme.surface,
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(20),
                        topRight: const Radius.circular(20),
                        bottomLeft: Radius.circular(msg.isUser ? 20 : 6),
                        bottomRight: Radius.circular(msg.isUser ? 6 : 20),
                      ),
                      border: msg.isUser
                          ? null
                          : Border.all(color: AppTheme.cardBorder, width: 1),
                      boxShadow: msg.isUser ? AppTheme.buttonShadow : AppTheme.softShadow,
                    ),
                    child: Text(
                      msg.text,
                      style: TextStyle(
                        color: msg.isUser ? Colors.white : AppTheme.textPrimary,
                        fontSize: 14.5,
                        height: 1.4,
                        fontWeight: msg.isUser ? FontWeight.w600 : FontWeight.normal,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),

          // Loading Thinking Indicator
          if (_isSending)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primary),
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'Coach is analyzing...',
                    style: TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),

          // Quick Suggestion Chips
          SizedBox(
            height: 42,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 20),
              itemCount: _quickPrompts.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, i) {
                return GestureDetector(
                  onTap: _isSending ? null : () => _sendMessage(_quickPrompts[i]),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceWarm,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: AppTheme.surfaceWarmBorder.withOpacity(0.6),
                      ),
                    ),
                    child: Text(
                      _quickPrompts[i],
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 10),

          // Bottom Input Bar
          Container(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              border: Border(top: BorderSide(color: AppTheme.cardBorder, width: 1)),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF1B224B).withOpacity(0.03),
                  blurRadius: 10,
                  offset: const Offset(0, -4),
                ),
              ],
            ),
            child: SafeArea(
              top: false,
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _textCtrl,
                      onSubmitted: (_) => _sendMessage(),
                      style: const TextStyle(color: AppTheme.textPrimary),
                      decoration: const InputDecoration(
                        hintText: 'Ask about training, form, or nutrition...',
                        contentPadding: EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  // Deep Navy Circular Send Button
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      gradient: AppTheme.primaryGradient,
                      shape: BoxShape.circle,
                      boxShadow: AppTheme.buttonShadow,
                    ),
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        customBorder: const CircleBorder(),
                        onTap: _isSending ? null : () => _sendMessage(),
                        child: const Icon(
                          Icons.arrow_upward_rounded,
                          color: Colors.white,
                          size: 22,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
