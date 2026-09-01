import os
import queue
import subprocess
import threading
import time

_queue = queue.Queue()
_started = False
_last_text = ""
_last_at = 0.0
_MIN_GAP = 2.2
_mode = "full"
_generation = 0
_current_proc = None
_proc_lock = threading.Lock()
_voice_gender = "Female"


def configure_voice(mode="full", cue_gap_seconds=4.0, gender="Female"):
    """full = normal talk, quiet = sparse cues, text = print only."""
    global _mode, _MIN_GAP, _voice_gender
    _mode = mode if mode in ("full", "quiet", "text") else "full"
    _voice_gender = gender if gender in ("Male", "Female") else "Female"
    gap = float(cue_gap_seconds or 4.0)
    if _mode == "quiet":
        _MIN_GAP = max(6.0, gap)
    else:
        _MIN_GAP = max(2.2, gap)


def _kill_current():
    global _current_proc
    with _proc_lock:
        proc = _current_proc
        _current_proc = None
    if proc is None:
        return

    def _kill():
        try:
            if os.name == "nt" and proc.pid:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=0.2)
        except Exception:
            pass

    threading.Thread(target=_kill, daemon=True).start()


def _speak_windows(text, generation):
    global _current_proc
    if generation != _generation:
        return
    safe = text.replace("'", "").replace('"', "")
    if not safe:
        return
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::{_voice_gender}); "
        f"$s.Speak('{safe}')"
    )
    try:
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return
    with _proc_lock:
        _current_proc = proc
    if generation != _generation:
        _kill_current()
        return
    proc.wait()
    with _proc_lock:
        if _current_proc is proc:
            _current_proc = None


def _worker():
    while True:
        item = _queue.get()
        if item is None:
            return
        text, generation = item
        try:
            if generation == _generation:
                _speak_windows(text, generation)
        except Exception:
            pass
        _queue.task_done()


def start_voice():
    global _started
    if _started:
        return
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    _started = True


def stop_voice():
    """Drop queued lines and kill speech that is already playing."""
    global _generation, _last_text
    _generation += 1
    _last_text = ""
    while True:
        try:
            _queue.get_nowait()
            _queue.task_done()
        except queue.Empty:
            break
    _kill_current()


def speak(text, force=False):
    """Queue a short coaching line. Drops repeats so we never dump six cues."""
    global _last_text, _last_at
    if not text:
        return
    cleaned = " ".join(text.split())
    if _mode == "text":
        print(f"[coach] {cleaned}")
        return
    now = time.time()
    if not force and cleaned == _last_text and now - _last_at < 6:
        return
    if not force and now - _last_at < _MIN_GAP:
        return
    start_voice()
    _last_text = cleaned
    _last_at = now
    while _queue.qsize() > 1:
        try:
            _queue.get_nowait()
            _queue.task_done()
        except queue.Empty:
            break
    _queue.put((cleaned, _generation))


def spoken_from_message(message):
    if not message:
        return ""
    text = message.split(":", 1)[-1].strip() if ":" in message else message
    return text.replace("{side}", "").replace("  ", " ").strip()
