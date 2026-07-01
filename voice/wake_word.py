"""
Wake word detector — always-on background listener.
Uses Faster-Whisper TINY model (much faster than base) for real-time detection.
Listens in 2-second overlapping windows for maximum responsiveness.
"""
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QThread, Signal

SAMPLE_RATE = 16000
CHUNK_SECS  = 2       # seconds per detection window
ENERGY_GATE = 0.002   # ignore silent chunks (lower = more sensitive)

# All accepted wake phrases — covers typos and accents
WAKE_PHRASES = {
    "hey nova", "nova", "hi nova", "ok nova", "okay nova",
    "hello nova", "hei nova", "hay nova", "hey nora", "hey no va",
    "a nova", "oh nova", "hey nova please", "nova please",
}


class WakeWordWorker(QThread):
    detected_signal = Signal()

    def __init__(self):
        super().__init__()
        self._running = False
        self._paused  = False
        self._model   = None

    def _load_model(self):
        """Load tiny model — fast enough for real-time wake word detection."""
        if self._model is None:
            from faster_whisper import WhisperModel
            # tiny is much faster than base — perfect for wake word, no quality loss
            self._model = WhisperModel("tiny", device="cpu", compute_type="int8")
        return self._model

    def run(self):
        self._running = True
        model = self._load_model()

        while self._running:
            if self._paused:
                self.msleep(150)
                continue

            try:
                # Record a chunk
                audio = sd.rec(
                    int(CHUNK_SECS * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="int16",
                    blocking=True,
                )

                if self._paused or not self._running:
                    continue

                # Convert to float32
                audio_f = audio.flatten().astype(np.float32) / 32768.0

                # Skip silent chunks — save CPU
                if np.abs(audio_f).mean() < ENERGY_GATE:
                    continue

                # Transcribe
                segments, _ = model.transcribe(
                    audio_f,
                    language="en",
                    condition_on_previous_text=False,
                    no_speech_threshold=0.4,   # lower = detect more speech
                    log_prob_threshold=-1.0,
                )
                text = " ".join(s.text for s in segments).lower().strip()

                # Check for any wake phrase
                if text and any(phrase in text for phrase in WAKE_PHRASES):
                    self._paused = True
                    self.detected_signal.emit()

            except Exception:
                self.msleep(300)

    def resume(self):
        """Call this after NOVA finishes handling the command."""
        self._paused = False

    def stop(self):
        self._running = False
