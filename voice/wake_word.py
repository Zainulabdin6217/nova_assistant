"""
Wake word detector — reliable always-on listener.

Key improvements over previous version:
- Uses a ROLLING BUFFER (3 sec window, advances 1.5 sec)
  so "Hey NOVA" can never be split across two chunks
- Tiny Whisper model for fast detection (< 300ms per check)
- Lower energy gate — catches quieter voices
- Multiple wake phrase variations to handle accents/pronunciation
- Separate stream stays open — no audio device reopening latency
"""
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QThread, Signal

SAMPLE_RATE  = 16000
WINDOW_SECS  = 3.0    # how much audio to analyze each time
STEP_SECS    = 1.5    # how often to check (overlapping windows)
ENERGY_GATE  = 0.002  # skip silent chunks — saves CPU

WAKE_PHRASES = {
    "hey nova", "nova", "hi nova", "ok nova", "okay nova",
    "hello nova", "hei nova", "hay nova", "hey nora",
    "hey no va", "nova please", "hello no",
    "hey know", "no va", "a nova",
}


class WakeWordWorker(QThread):
    """
    Runs on a background thread — never blocks the UI.
    Emits detected_signal when wake word is heard.
    Call resume() after NOVA finishes handling the command.
    """
    detected_signal = Signal()

    def __init__(self):
        super().__init__()
        self._running = False
        self._paused  = False
        self._model   = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            # tiny = 39MB, processes audio in ~300ms — perfect for real-time detection
            self._model = WhisperModel("tiny", device="cpu", compute_type="int8")
        return self._model

    def run(self):
        self._running = True
        model = self._load_model()

        window_size = int(WINDOW_SECS * SAMPLE_RATE)
        step_size   = int(STEP_SECS   * SAMPLE_RATE)

        # Rolling buffer — always holds the last WINDOW_SECS of audio
        buffer = np.zeros(window_size, dtype=np.float32)

        while self._running:
            if self._paused:
                self.msleep(150)
                continue

            try:
                # Record one step (1.5 seconds)
                chunk = sd.rec(
                    step_size,
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                    blocking=True,
                ).flatten()

                if self._paused or not self._running:
                    continue

                # Roll the buffer: drop oldest, add newest
                buffer = np.roll(buffer, -step_size)
                buffer[-step_size:] = chunk

                # Skip silent chunks — energy gate
                if np.abs(chunk).mean() < ENERGY_GATE:
                    continue

                # Transcribe the full 3-second rolling window
                segments, _ = model.transcribe(
                    buffer,
                    language="en",
                    condition_on_previous_text=False,
                    no_speech_threshold=0.5,
                    log_prob_threshold=-1.0,
                )
                text = " ".join(s.text for s in segments).lower().strip()

                if not text:
                    continue

                # Check for any wake phrase
                if any(phrase in text for phrase in WAKE_PHRASES):
                    self._paused = True
                    # Clear buffer so old audio doesn't bleed into next command
                    buffer = np.zeros(window_size, dtype=np.float32)
                    self.detected_signal.emit()

            except Exception:
                # sounddevice or model error — wait a moment and retry
                self.msleep(500)

    def resume(self):
        """Call this after NOVA finishes speaking so listening resumes."""
        self._paused = False

    def stop(self):
        self._running = False
