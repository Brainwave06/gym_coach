import 'dart:math' as math;
import 'dart:typed_data';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/services.dart';

/// Offline, zero-dependency audio & haptics feedback engine for workouts and UI interactions.
class SoundService {
  static final SoundService _instance = SoundService._internal();
  factory SoundService() => _instance;
  SoundService._internal();

  final AudioPlayer _player = AudioPlayer()..setReleaseMode(ReleaseMode.stop);

  Uint8List? _repChimeBytes;
  Uint8List? _faultAlertBytes;
  Uint8List? _completeFanfareBytes;

  /// Pre-generate synthesizer WAV audio buffers in memory
  void initialize() {
    _repChimeBytes ??= _generateChimeWav(
      frequencies: [880.0, 1318.5], // A5 + E6 chime chord
      durationSec: 0.35,
      decayRate: 8.0,
    );

    _faultAlertBytes ??= _generateChimeWav(
      frequencies: [220.0, 233.0], // Dissonant low buzz alert
      durationSec: 0.40,
      decayRate: 4.0,
    );

    _completeFanfareBytes ??= _generateArpeggioWav(
      notes: [523.25, 659.25, 783.99, 1046.5], // C5 - E5 - G5 - C6 triumph
      noteDurationSec: 0.12,
    );
  }

  /// Play clear energetic chime when a repetition is successfully completed
  Future<void> playRepChime() async {
    try {
      HapticFeedback.mediumImpact();
      initialize();
      if (_repChimeBytes != null) {
        await _player.stop();
        await _player.play(BytesSource(_repChimeBytes!));
      }
    } catch (_) {}
  }

  /// Play low urgent warning tone when a form error/fault is detected
  Future<void> playFaultAlert() async {
    try {
      HapticFeedback.heavyImpact();
      initialize();
      if (_faultAlertBytes != null) {
        await _player.stop();
        await _player.play(BytesSource(_faultAlertBytes!));
      }
    } catch (_) {}
  }

  /// Play victory fanfare when finishing a session
  Future<void> playWorkoutComplete() async {
    try {
      HapticFeedback.vibrate();
      initialize();
      if (_completeFanfareBytes != null) {
        await _player.stop();
        await _player.play(BytesSource(_completeFanfareBytes!));
      }
    } catch (_) {}
  }

  /// Subtle UI tick for interactive buttons
  void playTapFeedback() {
    try {
      HapticFeedback.selectionClick();
    } catch (_) {}
  }

  // --- WAV Synthesizer (Pure Dart PCM 16-bit Mono 44.1kHz) ---

  static Uint8List _generateChimeWav({
    required List<double> frequencies,
    required double durationSec,
    required double decayRate,
    int sampleRate = 44100,
  }) {
    final int numSamples = (sampleRate * durationSec).toInt();
    final int dataSize = numSamples * 2;
    final int fileSize = 44 + dataSize;

    final bytes = ByteData(fileSize);

    // RIFF header
    _writeString(bytes, 0, 'RIFF');
    bytes.setUint32(4, fileSize - 8, Endian.little);
    _writeString(bytes, 8, 'WAVE');

    // fmt subchunk
    _writeString(bytes, 12, 'fmt ');
    bytes.setUint32(16, 16, Endian.little); // Subchunk1Size (16 for PCM)
    bytes.setUint16(20, 1, Endian.little); // AudioFormat (1 = PCM)
    bytes.setUint16(22, 1, Endian.little); // NumChannels (1 = Mono)
    bytes.setUint32(24, sampleRate, Endian.little); // SampleRate
    bytes.setUint32(28, sampleRate * 2, Endian.little); // ByteRate (SampleRate * 1 channel * 2 bytes)
    bytes.setUint16(32, 2, Endian.little); // BlockAlign (1 channel * 2 bytes)
    bytes.setUint16(34, 16, Endian.little); // BitsPerSample (16 bits)

    // data subchunk
    _writeString(bytes, 36, 'data');
    bytes.setUint32(40, dataSize, Endian.little);

    // PCM Samples with exponential decay envelope
    int offset = 44;
    for (int i = 0; i < numSamples; i++) {
      final double t = i / sampleRate;
      final double envelope = math.exp(-decayRate * t);

      double sampleVal = 0.0;
      for (final freq in frequencies) {
        sampleVal += math.sin(2 * math.pi * freq * t);
      }
      sampleVal = (sampleVal / frequencies.length) * envelope;

      // Scale to 16-bit signed integer [-32768, 32767]
      final int sampleInt = (sampleVal * 28000).clamp(-32768, 32767).toInt();
      bytes.setInt16(offset, sampleInt, Endian.little);
      offset += 2;
    }

    return bytes.buffer.asUint8List();
  }

  static Uint8List _generateArpeggioWav({
    required List<double> notes,
    required double noteDurationSec,
    int sampleRate = 44100,
  }) {
    final int totalSamples = (sampleRate * noteDurationSec * notes.length).toInt();
    final int dataSize = totalSamples * 2;
    final int fileSize = 44 + dataSize;

    final bytes = ByteData(fileSize);

    _writeString(bytes, 0, 'RIFF');
    bytes.setUint32(4, fileSize - 8, Endian.little);
    _writeString(bytes, 8, 'WAVE');

    _writeString(bytes, 12, 'fmt ');
    bytes.setUint32(16, 16, Endian.little);
    bytes.setUint16(20, 1, Endian.little);
    bytes.setUint16(22, 1, Endian.little);
    bytes.setUint32(24, sampleRate, Endian.little);
    bytes.setUint32(28, sampleRate * 2, Endian.little);
    bytes.setUint16(32, 2, Endian.little);
    bytes.setUint16(34, 16, Endian.little);

    _writeString(bytes, 36, 'data');
    bytes.setUint32(40, dataSize, Endian.little);

    int offset = 44;
    final int samplesPerNote = (sampleRate * noteDurationSec).toInt();

    for (int n = 0; n < notes.length; n++) {
      final double freq = notes[n];
      for (int i = 0; i < samplesPerNote; i++) {
        final double t = i / sampleRate;
        final double envelope = math.exp(-3.5 * t);
        final double sampleVal = math.sin(2 * math.pi * freq * t) * envelope;
        final int sampleInt = (sampleVal * 28000).clamp(-32768, 32767).toInt();
        bytes.setInt16(offset, sampleInt, Endian.little);
        offset += 2;
      }
    }

    return bytes.buffer.asUint8List();
  }

  static void _writeString(ByteData data, int offset, String value) {
    for (int i = 0; i < value.length; i++) {
      data.setUint8(offset + i, value.codeUnitAt(i));
    }
  }

  void dispose() {
    _player.dispose();
  }
}
