import json
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QLineEdit, QPushButton, QMessageBox, QFrame,
    QScrollArea, QApplication, QSystemTrayIcon, QMenu,
)
from PySide6.QtCore  import Qt, QTimer
from PySide6.QtGui   import QFont, QPixmap, QPainter, QColor, QIcon, QAction

from ui.styles import DARK_THEME
from voice.recorder import Recorder
from voice.text_to_speech import speaker
from graph.workflow import is_confirmation_request, TIMER_MARKER
from utils.workers import CommandWorker, TranscriptionWorker, StatsWorker, WeatherWorker
from voice.wake_word import WakeWordWorker
from utils.startup import enable_startup, disable_startup, is_startup_enabled
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


def _make_tray_icon() -> QIcon:
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

        self.recorder        = Recorder()
        self._active_workers = []
        self._last_raw       = ""
        self._timer_secs     = 0
        self._timer_label    = None  # set in _build_ui

        self._build_ui()
        self._build_tray()
        self._start_stats()
        self._start_weather()
        self._refresh_history()

        self._set_status("Idle")
        self._append("NOVA", "Hello! I'm NOVA. Type or speak a command — or just say Hey NOVA!")
        self._check_api_key()
        self._init_startup_btn()
        self._start_wake_word()

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

        # header
        hdr = QHBoxLayout()
        title = QLabel("NOVA")
        title.setObjectName("TitleLabel")
        hdr.addWidget(title)
        hdr.addStretch()
        self.status_label = QLabel("Idle")
        self.status_label.setObjectName("StatusLabel")
        hdr.addWidget(self.status_label)
        left.addLayout(hdr)

        # chat
        self.chat_area = QTextEdit()
        self.chat_area.setObjectName("ChatArea")
        self.chat_area.setReadOnly(True)
        left.addWidget(self.chat_area, stretch=1)

        # countdown timer label (hidden by default)
        self._timer_label = QLabel("")
        self._timer_label.setAlignment(Qt.AlignCenter)
        self._timer_label.setStyleSheet(
            "color:#fdcb6e; font-size:18px; font-weight:700; padding:4px; background:#1a1a2e;"
            "border-radius:8px; border:1px solid #2a2a45;"
        )
        self._timer_label.hide()
        left.addWidget(self._timer_label)

        # input row
        inp = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type a command…")
        self.input_box.returnPressed.connect(self._on_send)
        inp.addWidget(self.input_box, stretch=1)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        inp.addWidget(self.send_btn)

        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setObjectName("MicButton")
        self.mic_btn.clicked.connect(self._on_mic)
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

        # Weather section
        wx_lbl = QLabel("WEATHER")
        wx_lbl.setObjectName("SectionLabel")
        rl.addWidget(wx_lbl)

        self.wx_city  = QLabel("—")
        self.wx_city.setObjectName("StatLabel")
        rl.addWidget(self.wx_city)
        self.wx_temp  = QLabel("—")
        self.wx_temp.setObjectName("StatValue")
        rl.addWidget(self.wx_temp)
        self.wx_desc  = QLabel("—")
        self.wx_desc.setObjectName("StatLabel")
        rl.addWidget(self.wx_desc)

        # System section
        sys_lbl = QLabel("SYSTEM")
        sys_lbl.setObjectName("SectionLabel")
        rl.addWidget(sys_lbl)
        self.cpu_val     = self._stat_row(rl, "CPU")
        self.ram_val     = self._stat_row(rl, "RAM")
        self.battery_val = self._stat_row(rl, "Battery")
        self.time_val    = self._stat_row(rl, "Time")

        # History section
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

    # ── System tray ─────────────────────────────────────────────────────────
    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(_make_tray_icon())
        self.tray.setToolTip("NOVA Voice Assistant")

        menu = QMenu()
        open_action = QAction("Open NOVA", self)
        open_action.triggered.connect(self.show)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "NOVA", "Still running in the system tray. Right-click the icon to quit.",
            QSystemTrayIcon.MessageIcon.Information, 2000,
        )

    # ── Countdown timer ──────────────────────────────────────────────────────
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
            self._append("NOVA", "⏰ Timer finished!")
            speaker.speak("Timer done!")
            QTimer.singleShot(4000, self._timer_label.hide)
        else:
            m, s = divmod(self._timer_secs, 60)
            h, m = divmod(m, 60)
            if h:
                txt = f"⏱ {h:02d}:{m:02d}:{s:02d}"
            else:
                txt = f"⏱ {m:02d}:{s:02d}"
            self._timer_label.setText(txt)

    # ── Status + chat helpers ────────────────────────────────────────────────
    def _set_status(self, status: str):
        self.status_label.setText(status)
        color = STATUS_COLORS.get(status, "#6c5ce7")
        self.status_label.setStyleSheet(
            f"background-color:#1a1a2e;color:{color};padding:6px 14px;"
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
            self._append("NOVA", "✓ Using OpenAI (gpt-4o-mini). Ready!")
        elif provider == "ollama":
            self._append("NOVA", "✓ Using local Ollama (llama3.2:3b) — free & offline. Ready!")
        else:
            self._append(
                "NOVA",
                "⚠ No AI provider found. Either:\n"
                "  • Add OPENAI_API_KEY to your .env file, OR\n"
                "  • Install Ollama from ollama.com and run: ollama pull llama3.2:3b"
            )

    # ── Send / handle ────────────────────────────────────────────────────────
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
        w = CommandWorker(text, confirmed=confirmed, intent=intent, args=args, skip_classify=skip)
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
            self._append("NOVA", "Stopped speaking.")
            self._set_status("Idle")
            self._resume_wake()
            return

        if response == "__CLEAR_CHAT__":
            self.chat_area.clear()
            self._append("NOVA", "Chat cleared.")
            self._set_status("Idle")
            self._resume_wake()
            return

        # Timer
        if response.startswith(TIMER_MARKER):
            rest  = response[len(TIMER_MARKER):]
            parts = rest.split("|", 1)
            secs  = int(parts[0])
            label = parts[1] if len(parts) > 1 else f"{secs}s timer"
            self._append("NOVA", label)
            speaker.speak(label)
            self._start_timer(secs, label)
            self._set_status("Idle")
            self._resume_wake()
            return

        # Confirmation request
        is_confirm, intent, target, orig_args = is_confirmation_request(response)
        if is_confirm:
            self._set_status("Idle")
            self._show_confirm_dialog(intent, target, orig_args)
            # wake word resumes after confirm dialog finishes in _on_done again
            return

        self._set_status("Speaking")
        self._append("NOVA", response)
        self._refresh_history()
        speaker.speak(response)
        self._set_status("Idle")
        self._resume_wake()

    def _show_confirm_dialog(self, intent, target, orig_args):
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
        self._append("NOVA", f"Error: {err}")
        self._resume_wake()

    def _set_enabled(self, enabled: bool):
        self.send_btn.setEnabled(enabled)
        self.input_box.setEnabled(enabled)
        self.mic_btn.setEnabled(enabled)

    def _cleanup(self, w):
        if w in self._active_workers:
            self._active_workers.remove(w)

    # ── Voice ────────────────────────────────────────────────────────────────
    def _on_mic(self):
        if not self.recorder.is_recording:
            self.recorder.start()
            self.mic_btn.setText("⏹")
            self.mic_btn.setProperty("recording", "true")
            self.mic_btn.setStyle(self.mic_btn.style())
            self._set_status("Listening")
        else:
            path = self.recorder.stop()
            self.mic_btn.setText("🎙")
            self.mic_btn.setProperty("recording", "false")
            self.mic_btn.setStyle(self.mic_btn.style())
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
            self._append("NOVA", "Didn't catch that — try again.")
            self._set_status("Idle")
            return
        self.input_box.setText(text)
        self._append("You", text)
        self._run(text)

    # ── Buttons ──────────────────────────────────────────────────────────────
    def _on_stop_speaking(self):
        speaker.stop()
        self._set_status("Idle")

    def _on_clear(self):
        self.chat_area.clear()
        self._append("NOVA", "Chat cleared. How can I help?")

    # ── Stats polling ────────────────────────────────────────────────────────
    def _start_stats(self):
        self.stats_worker = StatsWorker()
        self.stats_worker.stats_signal.connect(self._on_stats)
        self.stats_worker.start()

    def _on_stats(self, s: dict):
        self.cpu_val.setText(f"{s['cpu']}%")
        self.ram_val.setText(f"{s['ram']}%")
        self.battery_val.setText(f"{s['battery']}%" if s["battery"] is not None else "N/A")
        self.time_val.setText(s["time"])

    # ── Weather ──────────────────────────────────────────────────────────────
    def _start_weather(self):
        self.wx_worker = WeatherWorker("Lahore")
        self.wx_worker.weather_signal.connect(self._on_weather)
        self.wx_worker.start()

    def _on_weather(self, d: dict):
        self.wx_city.setText(d["city"])
        self.wx_temp.setText(f"{d['temp']}°C (feels {d['feels']}°C)")
        self.wx_desc.setText(f"{d['desc']} · {d['humidity']}% humidity")

    # ── Recent history ───────────────────────────────────────────────────────
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

    # ── Wake word ────────────────────────────────────────────────────────────
    def _start_wake_word(self):
        self.wake_worker = WakeWordWorker()
        self.wake_worker.detected_signal.connect(self._on_wake_word)
        self.wake_worker.start()
        self._append("NOVA", "Wake word active — say 'Hey NOVA' to start listening.")

    def _on_wake_word(self):
        self._set_status("Listening")
        self._append("NOVA", "Wake word detected — listening…")
        self.recorder.start()
        # Record for 4 seconds then auto-stop and transcribe
        QTimer.singleShot(4000, self._auto_stop_recording)

    def _auto_stop_recording(self):
        if self.recorder.is_recording:
            path = self.recorder.stop()
            self._set_status("Transcribing")
            self._set_enabled(False)
            w = TranscriptionWorker(path)
            w.finished_signal.connect(self._on_transcript_wake)
            w.error_signal.connect(self._on_error)
            w.finished_signal.connect(lambda _: self._cleanup(w))
            w.error_signal.connect(lambda _: self._cleanup(w))
            self._active_workers.append(w)
            w.start()

    def _on_transcript_wake(self, text: str):
        self._set_enabled(True)
        if not text.strip():
            self._append("NOVA", "I heard the wake word but couldn't catch the command — say Hey NOVA again.")
            self._set_status("Idle")
            self._resume_wake()
            return
        self._append("You", text)
        self._run(text)
        # Note: _resume_wake is called inside _on_done after command finishes

    # ── Startup toggle ────────────────────────────────────────────────────────
    def _init_startup_btn(self):
        enabled = is_startup_enabled()
        self._startup_btn.setText("✓ Auto-start ON" if enabled else "Auto-start OFF")
        self._startup_btn.setStyleSheet(
            "background:#00b894;" if enabled else "background:#2a2a45;"
        )

    def _toggle_startup(self):
        if is_startup_enabled():
            msg = disable_startup()
        else:
            msg = enable_startup()
        self._append("NOVA", msg)
        self._init_startup_btn()

    # ── Cleanup ──────────────────────────────────────────────────────────────
    def real_quit(self):
        self.stats_worker.stop()
        self.wx_worker.stop()
        if hasattr(self, 'wake_worker'):
            self.wake_worker.stop()
            self.wake_worker.wait(400)
        self.stats_worker.wait(400)
        self.wx_worker.wait(400)
        speaker.stop()
        QApplication.quit()
