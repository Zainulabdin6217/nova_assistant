import numpy as np
from faster_whisper import WhisperModel

_model = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> str:
    """Transcribe a .wav file on disk."""
    model = _get_model()
    segments, _ = model.transcribe(audio_path, language="en")
    return " ".join(s.text for s in segments).strip()


def transcribe_array(audio_array: np.ndarray) -> str:
    """
    Transcribe a raw float32 numpy array (16kHz mono, values -1..1).
    Used by the wake-word detector to avoid writing temp files.
    """
    model = _get_model()
    segments, _ = model.transcribe(audio_array, language="en")
    return " ".join(s.text for s in segments).strip()
