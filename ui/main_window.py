import json
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QLineEdit, QPushButton, QMessageBox, QFrame,
    QScrollArea, QApplication, QSystemTrayIcon, QMenu, QCheckBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QIcon, QAction

from ui.styles import DARK_THEME
from voice.recorder import Recorder
from voice.text_to_speech import speaker
from voice.wake_word import WakeWordWorker
from graph.workflow import is_confirmation_request, TIMER_MARKER
from utils.workers import CommandWorker, TranscriptionWorker, StatsWorker, WeatherWorker
from utils.hotkey import HotkeyWorker, stop_all_hotkeys
from database.database import db

STATUS_COLORS = {
    "Idle":         "#6c5ce7",
    "Listening":    "#e84393",
    "Transcribing": "#fdcb6e",
    "Thinking":     "#00cec9",
    "Executing":    "#0984e3",
    "Speaking":     "#00b894",
    "Completed":    "#6c5ce7",
    "Error":        "#d63031",
}


def _make_icon() -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#6c5ce7"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(1, 1, 30, 30)
    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI", 14, QFont.Bold))
    p.drawText(pix.rect(), Qt.AlignCenter, "N")
    p.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOVA — Desktop Voice Assistant")
        self.resize(1020, 660)
        self.setStyleSheet(DARK_THEME)
        self.setWindowIcon(_make_icon())

        self.recorder        = Recorder()
        self._active_workers = []
        self._last_raw       = ""
        self._timer_secs     = 0
        self._timer_label    = None  # set in _build_ui
        self._recording_now  = False

        self._build_ui()
        self._build_tray()
        self._start_stats()
        self._start_weather()
        self._start_hotkey()
        self._start_wake_word()
        self._refresh_history()

        self._set_status("Idle")
        self._greet()
        self._check_api_key()

    # ── Greeting ─────────────────────────────────────────────────────────────
    def _greet(self):
        msg = "Hi! I'm NOVA. Press Ctrl+Space anywhere or say 'Hey NOVA' to give a command."
        self._append("NOVA", msg)
        QTimer.singleShot(500, lambda: speaker.speak(msg))

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # ── Left panel ──
        left = QVBoxLayout()
        left.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("NOVA")
        title.setObjectName("TitleLabel")
        hdr.addWidget(title)
        hdr.addStretch()
        self.status_label = QLabel("Idle")
        self.status_label.setObjectName("StatusLabel")
        hdr.addWidget(self.status_label)
        left.addLayout(hdr)

        self.chat_area = QTextEdit()
        self.chat_area.setObjectName("ChatArea")
        self.chat_area.setReadOnly(True)
        left.addWidget(self.chat_area, stretch=1)

        # countdown timer label
        self._timer_label = QLabel("")
        self._timer_label.setAlignment(Qt.AlignCenter)
        self._timer_label.setStyleSheet(
            "color:#fdcb6e;font-size:18px;font-weight:700;padding:4px;"
            "background:#1a1a2e;border-radius:8px;border:1px solid #2a2a45;"
        )
        self._timer_label.hide()
        left.addWidget(self._timer_label)

        # input row
        inp = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type a command… or press Ctrl+Space to speak")
        self.input_box.returnPressed.connect(self._on_send)
        inp.addWidget(self.input_box, stretch=1)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        inp.addWidget(self.send_btn)

        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setObjectName("MicButton")
        self.mic_btn.clicked.connect(self._on_mic)
        self.mic_btn.setToolTip("Click to record, or press Ctrl+Space anywhere")
        inp.addWidget(self.mic_btn)
        left.addLayout(inp)

        # action row
        act = QHBoxLayout()
        stop_btn = QPushButton("Stop Speaking")
        stop_btn.setObjectName("StopButton")
        stop_btn.clicked.connect(self._on_stop_speaking)
        act.addWidget(stop_btn)

        clr_btn = QPushButton("Clear")
        clr_btn.setObjectName("ClearButton")
        clr_btn.clicked.connect(self._on_clear)
        act.addWidget(clr_btn)

        # Wake word toggle checkbox
        self._wake_cb = QCheckBox("Hey NOVA (wake word)")
        self._wake_cb.setStyleSheet("color:#8892b0;font-size:12px;padding-left:4px;")
        self._wake_cb.setToolTip("Enable to say 'Hey NOVA' to activate (uses more CPU)")
        self._wake_cb.stateChanged.connect(self._on_wake_toggle)
        act.addWidget(self._wake_cb)

        # Startup toggle
        self._startup_btn = QPushButton()
        self._startup_btn.clicked.connect(self._toggle_startup)
        act.addWidget(self._startup_btn)
        act.addStretch()
        left.addLayout(act)

        root.addLayout(left, stretch=3)

        # ── Right panel ──
        right = QFrame()
        right.setObjectName("SidePanel")
        right.setFixedWidth(240)
        rl = QVBoxLayout(right)
        rl.setSpacing(4)

        wx_lbl = QLabel("WEATHER")
        wx_lbl.setObjectName("SectionLabel")
        rl.addWidget(wx_lbl)

        self.wx_city = QLabel("—")
        self.wx_city.setObjectName("StatLabel")
        rl.addWidget(self.wx_city)
        self.wx_temp = QLabel("—")
        self.wx_temp.setObjectName("StatValue")
        rl.addWidget(self.wx_temp)
        self.wx_desc = QLabel("—")
        self.wx_desc.setObjectName("StatLabel")
        rl.addWidget(self.wx_desc)

        sys_lbl = QLabel("SYSTEM")
        sys_lbl.setObjectName("SectionLabel")
        rl.addWidget(sys_lbl)
        self.cpu_val     = self._stat_row(rl, "CPU")
        self.ram_val     = self._stat_row(rl, "RAM")
        self.battery_val = self._stat_row(rl, "Battery")
        self.time_val    = self._stat_row(rl, "Time")

        hist_lbl = QLabel("RECENT COMMANDS")
        hist_lbl.setObjectName("SectionLabel")
        rl.addWidget(hist_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:transparent;border:none;")
        self._hist_container = QWidget()
        self._hist_layout    = QVBoxLayout(self._hist_container)
        self._hist_layout.setSpacing(3)
        self._hist_layout.addStretch()
        scroll.setWidget(self._hist_container)
        rl.addWidget(scroll, stretch=1)

        root.addWidget(right)

    def _stat_row(self, layout, label_text) -> QLabel:
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setObjectName("StatLabel")
        val = QLabel("—")
        val.setObjectName("StatValue")
        val.setAlignment(Qt.AlignRight)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)
        return val

    # ── System tray ──────────────────────────────────────────────────────────
    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(_make_icon())
        self.tray.setToolTip("NOVA — Press Ctrl+Space to activate")
        menu = QMenu()
        open_a = QAction("Open NOVA", self)
        open_a.triggered.connect(self.show)
        quit_a = QAction("Quit", self)
        quit_a.triggered.connect(self.real_quit)
        menu.addAction(open_a)
        menu.addSeparator()
        menu.addAction(quit_a)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show(); self.raise_()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "NOVA", "Running in tray — Ctrl+Space to activate. Right-click icon to quit.",
            QSystemTrayIcon.MessageIcon.Information, 2000,
        )

    # ── Countdown timer ───────────────────────────────────────────────────────
    def _start_timer(self, seconds: int, label: str):
        self._timer_secs = seconds
        self._timer_label.setText(f"⏱ {label}")
        self._timer_label.show()
        self._qt_timer = QTimer(self)
        self._qt_timer.setInterval(1000)
        self._qt_timer.timeout.connect(self._tick_timer)
        self._qt_timer.start()

    def _tick_timer(self):
        self._timer_secs -= 1
        if self._timer_secs <= 0:
            self._qt_timer.stop()
            self._timer_label.setText("⏱ Timer done!")
            done_msg = "Timer finished!"
            self._append("NOVA", f"⏰ {done_msg}")
            speaker.speak(done_msg)
            QTimer.singleShot(4000, self._timer_label.hide)
        else:
            m, s = divmod(self._timer_secs, 60)
            h, m = divmod(m, 60)
            txt = f"⏱ {h:02d}:{m:02d}:{s:02d}" if h else f"⏱ {m:02d}:{s:02d}"
            self._timer_label.setText(txt)

    # ── Status + chat ─────────────────────────────────────────────────────────
    def _set_status(self, status: str):
        self.status_label.setText(status)
        color = STATUS_COLORS.get(status, "#6c5ce7")
        self.status_label.setStyleSheet(
            f"background:#1a1a2e;color:{color};padding:6px 14px;"
            f"border-radius:14px;font-weight:600;"
        )

    def _append(self, sender: str, text: str):
        color = "#8b7cf6" if sender == "NOVA" else "#00cec9"
        self.chat_area.append(
            f'<p style="margin:5px 0"><b style="color:{color}">{sender}:</b> '
            f'<span style="color:#e0e0f0">{text}</span></p>'
        )
        self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()
        )

    def _check_api_key(self):
        from utils import llm_brain
        provider = llm_brain.active_provider()
        if provider == "openai":
            msg = "✓ Using OpenAI (gpt-4o-mini). Ready!"
        elif provider == "ollama":
            msg = "✓ Using local Ollama. Ready!"
        else:
            msg = "⚠ No AI provider. Add OPENAI_API_KEY to .env or install Ollama."
        self._append("NOVA", msg)
        self._init_startup_btn()

    # ── Send / handle ──────────────────────────────────────────────────────
    def _on_send(self):
        text = self.input_box.text().strip()
        if not text:
            return
        self.input_box.clear()
        self._append("You", text)
        self._run(text)

    def _run(self, text: str, confirmed=None, intent=None, args=None, skip=False):
        self._last_raw = text
        self._set_status("Thinking")
        self._set_enabled(False)
        w = CommandWorker(text, confirmed=confirmed, intent=intent,
                         args=args, skip_classify=skip)
        w.finished_signal.connect(self._on_done)
        w.error_signal.connect(self._on_error)
        w.finished_signal.connect(lambda _: self._cleanup(w))
        w.error_signal.connect(lambda _: self._cleanup(w))
        self._active_workers.append(w)
        w.start()

    def _on_done(self, result: dict):
        self._set_enabled(True)
        response = result.get("response", "")

        if response == "__STOP_SPEAKING__":
            speaker.stop()
            msg = "Stopped speaking."
            self._append("NOVA", msg)
            self._set_status("Idle")
            self._resume_inputs()
            return

        if response == "__CLEAR_CHAT__":
            self.chat_area.clear()
            msg = "Chat cleared."
            self._append("NOVA", msg)
            speaker.speak(msg)
            self._set_status("Idle")
            self._resume_inputs()
            return

        # Timer marker
        if response.startswith(TIMER_MARKER):
            rest  = response[len(TIMER_MARKER):]
            parts = rest.split("|", 1)
            secs  = int(parts[0])
            label = parts[1] if len(parts) > 1 else f"{secs}s timer"
            self._append("NOVA", label)
            speaker.speak(label)
            self._start_timer(secs, label)
            self._set_status("Idle")
            self._resume_inputs()
            return

        # Confirmation dialog
        is_confirm, intent, target, orig_args = is_confirmation_request(response)
        if is_confirm:
            self._set_status("Idle")
            self._show_confirm_dialog(intent, target, orig_args)
            return

        # Normal response — show AND speak it
        self._set_status("Speaking")
        self._append("NOVA", response)
        self._refresh_history()
        speaker.speak(response)
        self._set_status("Idle")
        self._resume_inputs()

    def _show_confirm_dialog(self, intent, target, orig_args):
        ask_msg = f"Are you sure? Target: {target}"
        speaker.speak(ask_msg)
        box = QMessageBox(self)
        box.setWindowTitle("Confirm Action")
        box.setText(f"Are you sure you want to proceed?\n\nTarget: {target}")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        box.setStyleSheet("QLabel{color:#e0e0f0}QWidget{background-color:#1a1a2e}")
        confirmed = box.exec() == QMessageBox.Yes
        self._run(self._last_raw, confirmed=confirmed, intent=intent,
                  args=orig_args, skip=True)

    def _on_error(self, err: str):
        self._set_enabled(True)
        self._set_status("Error")
        err_msg = f"Error: {err}"
        self._append("NOVA", err_msg)
        speaker.speak(err_msg)
        self._resume_inputs()

    def _set_enabled(self, enabled: bool):
        self.send_btn.setEnabled(enabled)
        self.input_box.setEnabled(enabled)
        self.mic_btn.setEnabled(enabled)

    def _resume_inputs(self):
        """Re-enable hotkey + wake word after NOVA finishes."""
        if hasattr(self, "hotkey_worker") and self.hotkey_worker.isRunning():
            self.hotkey_worker.resume()
        if hasattr(self, "wake_worker") and self.wake_worker.isRunning():
            self.wake_worker.resume()

    def _cleanup(self, w):
        if w in self._active_workers:
            self._active_workers.remove(w)

    # ── Mic button ────────────────────────────────────────────────────────────
    def _on_mic(self):
        self._start_recording()

    def _start_recording(self):
        if self._recording_now:
            return
        self._recording_now = True
        self.recorder.start()
        self.mic_btn.setText("⏹")
        self._set_status("Listening")
        speaker.speak("Listening")
        QTimer.singleShot(4000, self._finish_recording)

    def _finish_recording(self):
        if not self._recording_now:
            return
        self._recording_now = False
        path = self.recorder.stop()
        self.mic_btn.setText("🎙")
        self._set_status("Transcribing")
        self._set_enabled(False)
        w = TranscriptionWorker(path)
        w.finished_signal.connect(self._on_transcript)
        w.error_signal.connect(self._on_error)
        w.finished_signal.connect(lambda _: self._cleanup(w))
        w.error_signal.connect(lambda _: self._cleanup(w))
        self._active_workers.append(w)
        w.start()

    def _on_transcript(self, text: str):
        self._set_enabled(True)
        if not text.strip():
            not_caught = "Didn't catch that — try again."
            self._append("NOVA", not_caught)
            speaker.speak(not_caught)
            self._set_status("Idle")
            self._resume_inputs()
            return
        self._append("You", text)
        self._run(text)

    def _on_stop_speaking(self):
        speaker.stop()
        self._set_status("Idle")

    def _on_clear(self):
        self.chat_area.clear()
        self._append("NOVA", "Chat cleared.")

    # ── Hotkey ────────────────────────────────────────────────────────────────
    def _start_hotkey(self):
        self.hotkey_worker = HotkeyWorker()
        self.hotkey_worker.detected_signal.connect(self._on_hotkey)
        self.hotkey_worker.start()

    def _on_hotkey(self):
        self._append("NOVA", "Hotkey — listening...")
        self._start_recording()

    # ── Wake word (optional toggle) ───────────────────────────────────────────
    def _start_wake_word(self):
        self.wake_worker = WakeWordWorker()
        self.wake_worker.detected_signal.connect(self._on_wake_word)
        # NOT started yet — user must enable checkbox

    def _on_wake_toggle(self, state):
        enabled = bool(state)
        if enabled:
            if not self.wake_worker.isRunning():
                self.wake_worker.start()
            msg = "Wake word enabled. Say 'Hey NOVA' to activate."
            self._append("NOVA", msg)
            speaker.speak(msg)
        else:
            if self.wake_worker.isRunning():
                self.wake_worker.stop()
                self.wake_worker.wait(500)
                self.wake_worker = WakeWordWorker()
                self.wake_worker.detected_signal.connect(self._on_wake_word)
            msg = "Wake word disabled."
            self._append("NOVA", msg)
            speaker.speak(msg)

    def _on_wake_word(self):
        self._append("NOVA", "Hey NOVA detected — listening...")
        self._start_recording()

    # ── Stats ─────────────────────────────────────────────────────────────────
    def _start_stats(self):
        self.stats_worker = StatsWorker()
        self.stats_worker.stats_signal.connect(self._on_stats)
        self.stats_worker.start()

    def _on_stats(self, s: dict):
        self.cpu_val.setText(f"{s['cpu']}%")
        self.ram_val.setText(f"{s['ram']}%")
        self.battery_val.setText(f"{s['battery']}%" if s["battery"] is not None else "N/A")
        self.time_val.setText(s["time"])

    # ── Weather ───────────────────────────────────────────────────────────────
    def _start_weather(self):
        self.wx_worker = WeatherWorker("Lahore")
        self.wx_worker.weather_signal.connect(self._on_weather)
        self.wx_worker.start()

    def _on_weather(self, d: dict):
        self.wx_city.setText(d["city"])
        self.wx_temp.setText(f"{d['temp']}°C (feels {d['feels']}°C)")
        self.wx_desc.setText(f"{d['desc']} · {d['humidity']}% humidity")

    # ── History ───────────────────────────────────────────────────────────────
    def _refresh_history(self):
        while self._hist_layout.count() > 1:
            item = self._hist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for entry in db.get_history(limit=8):
            icon  = "✓" if entry["success"] else "✗"
            color = "#00b894" if entry["success"] else "#d63031"
            lbl   = QLabel(f"{icon} {entry['command'][:28]}")
            lbl.setStyleSheet(f"color:{color};font-size:11px;padding:2px 0;")
            lbl.setWordWrap(True)
            self._hist_layout.insertWidget(self._hist_layout.count() - 1, lbl)

    # ── Startup toggle ────────────────────────────────────────────────────────
    def _init_startup_btn(self):
        from utils.startup import is_startup_enabled
        enabled = is_startup_enabled()
        self._startup_btn.setText("✓ Auto-start ON" if enabled else "Auto-start OFF")
        self._startup_btn.setStyleSheet(
            "background:#00b894;" if enabled else "background:#2a2a45;"
        )

    def _toggle_startup(self):
        from utils.startup import enable_startup, disable_startup, is_startup_enabled
        msg = disable_startup() if is_startup_enabled() else enable_startup()
        self._append("NOVA", msg)
        speaker.speak(msg)
        self._init_startup_btn()

    # ── Quit ─────────────────────────────────────────────────────────────────
    def real_quit(self):
        self.stats_worker.stop()
        self.wx_worker.stop()
        if self.wake_worker.isRunning():
            self.wake_worker.stop()
            self.wake_worker.wait(400)
        if self.hotkey_worker.isRunning():
            self.hotkey_worker.stop()
            self.hotkey_worker.wait(400)
        self.stats_worker.wait(400)
        self.wx_worker.wait(400)
        speaker.stop()
        stop_all_hotkeys()
        QApplication.quit()
