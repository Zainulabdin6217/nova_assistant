from faster_whisper import WhisperModel

# "base" model is a good balance of speed and accuracy for an offline demo.
# Downloads once on first run (~150MB), then cached locally.
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> str:
    model = _get_model()
    segments, _info = model.transcribe(audio_path, language="en")
    text = " ".join(segment.text for segment in segments).strip()
    return text
