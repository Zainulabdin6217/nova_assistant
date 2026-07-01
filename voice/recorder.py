import sounddevice as sd
import numpy as np
from pathlib import Path
import wave

SAMPLE_RATE = 16000  # Whisper expects 16kHz
RECORDING_PATH = Path(__file__).parent.parent / "temp_recording.wav"


class Recorder:
    """
    Records audio from the microphone in a background thread-safe way.
    Call start() to begin, stop() to finish and save the .wav file.
    """

    def __init__(self):
        self._frames = []
        self._stream = None
        self.is_recording = False

    def _callback(self, indata, frames, time_info, status):
        self._frames.append(indata.copy())

    def start(self):
        self._frames = []
        self.is_recording = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> str:
        if not self.is_recording:
            return str(RECORDING_PATH)

        self.is_recording = False
        self._stream.stop()
        self._stream.close()

        if not self._frames:
            return str(RECORDING_PATH)

        audio_data = np.concatenate(self._frames, axis=0)

        with wave.open(str(RECORDING_PATH), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())

        return str(RECORDING_PATH)
