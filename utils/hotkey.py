"""
Global hotkey listener.
Waits for Ctrl+Space anywhere on Windows, then triggers voice recognition.
Runs on its own thread so UI is never blocked.
"""
import keyboard
from PySide6.QtCore import QThread, Signal


class HotkeyWorker(QThread):
    """
    Listens for Ctrl+Space globally using the keyboard package.
    Never blocks — UI and wake word stay responsive.
    """
    detected_signal = Signal()

    def __init__(self):
        super().__init__()
        self._running = False
        self._listening = True

    def run(self):
        keyboard.unhook_all()  # remove any previous hooks
        keyboard.add_hotkey("ctrl+space", self._hotkey_pressed)
        self._running = True
        while self._running:
            if not self._listening:
                self.msleep(200)  # let NOVA process current request
                continue
            keyboard.wait()

    def _hotkey_pressed(self):
        self._listening = False
        self.detected_signal.emit()

    def resume(self):
        """Resume hotkey listening after NOVA completes current request."""
        self._listening = True

    def stop(self):
        self._running = False
        keyboard.unhook_all()


def stop_all_hotkeys():
    """Call on app quit to avoid hotkey staying active."""
    keyboard.unhook_all()
