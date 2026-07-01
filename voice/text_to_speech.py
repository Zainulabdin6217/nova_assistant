import pyttsx3
import threading


class Speaker:
    """
    Wraps pyttsx3 so it can speak without freezing the UI thread,
    and supports being stopped mid-sentence.
    """

    def __init__(self):
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", 175)
        self._thread = None
        self._stop_flag = False

    def speak(self, text: str):
        if not text:
            return
        self._stop_flag = False
        self._thread = threading.Thread(target=self._speak_worker, args=(text,), daemon=True)
        self._thread.start()

    def _speak_worker(self, text: str):
        if self._stop_flag:
            return
        self._engine.say(text)
        self._engine.runAndWait()

    def stop(self):
        self._stop_flag = True
        try:
            self._engine.stop()
        except Exception:
            pass


speaker = Speaker()
