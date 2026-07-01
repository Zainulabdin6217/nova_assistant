from PySide6.QtCore import QThread, Signal

from graph.workflow import run_command
from voice.speech_to_text import transcribe


class CommandWorker(QThread):
    finished_signal = Signal(dict)
    error_signal    = Signal(str)

    def __init__(self, command_text, confirmed=None, intent=None, args=None, skip_classify=False):
        super().__init__()
        self.command_text  = command_text
        self.confirmed     = confirmed
        self.intent        = intent
        self.args          = args
        self.skip_classify = skip_classify

    def run(self):
        try:
            result = run_command(
                self.command_text,
                confirmed=self.confirmed,
                intent=self.intent,
                args=self.args,
                skip_classify=self.skip_classify,
            )
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class TranscriptionWorker(QThread):
    finished_signal = Signal(str)
    error_signal    = Signal(str)

    def __init__(self, audio_path):
        super().__init__()
        self.audio_path = audio_path

    def run(self):
        try:
            self.finished_signal.emit(transcribe(self.audio_path))
        except Exception as e:
            self.error_signal.emit(str(e))


class StatsWorker(QThread):
    stats_signal = Signal(dict)

    def __init__(self):
        super().__init__()
        self._running = True

    def run(self):
        from tools.system_tools import get_stats_snapshot
        while self._running:
            try:
                self.stats_signal.emit(get_stats_snapshot())
            except Exception:
                pass
            self.msleep(1000)

    def stop(self):
        self._running = False


class WeatherWorker(QThread):
    weather_signal = Signal(dict)

    def __init__(self, city="Lahore"):
        super().__init__()
        self.city     = city
        self._running = True

    def run(self):
        from tools.info_tools import get_weather_snapshot
        while self._running:
            try:
                data = get_weather_snapshot(self.city)
                if data:
                    self.weather_signal.emit(data)
            except Exception:
                pass
            # Refresh every 10 minutes
            for _ in range(600):
                if not self._running:
                    return
                self.msleep(1000)

    def stop(self):
        self._running = False
