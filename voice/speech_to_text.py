<<<<<<< HEAD
import numpy as np
from faster_whisper import WhisperModel

_model = None


def _get_model() -> WhisperModel:
=======
from faster_whisper import WhisperModel

# "base" model is a good balance of speed and accuracy for an offline demo.
# Downloads once on first run (~150MB), then cached locally.
_model = None


def _get_model():
>>>>>>> d62f4e2dc05d561969deec9ac1c3f93d18a72b06
    global _model
    if _model is None:
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> str:
<<<<<<< HEAD
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
=======
    model = _get_model()
    segments, _info = model.transcribe(audio_path, language="en")
    text = " ".join(segment.text for segment in segments).strip()
    return text
>>>>>>> d62f4e2dc05d561969deec9ac1c3f93d18a72b06
