DARK_THEME = """
QWidget {
    background-color: #0f0f1a;
    color: #e0e0f0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0f0f1a;
}

#TitleLabel {
    font-size: 22px;
    font-weight: 700;
    color: #8b7cf6;
    padding: 6px 0;
}

#StatusLabel {
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 14px;
    background-color: #1a1a2e;
    color: #6c5ce7;
}

#ChatArea {
    background-color: #15152a;
    border: 1px solid #2a2a45;
    border-radius: 10px;
    padding: 10px;
}

QTextEdit, QLineEdit {
    background-color: #1a1a2e;
    border: 1px solid #2a2a45;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e0e0f0;
    selection-background-color: #6c5ce7;
}

QLineEdit:focus {
    border: 1px solid #8b7cf6;
}

QPushButton {
    background-color: #6c5ce7;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #7d6ff0;
}

QPushButton:pressed {
    background-color: #5b4dd1;
}

QPushButton:disabled {
    background-color: #3a3a55;
    color: #777799;
}

#MicButton {
    background-color: #00cec9;
    border-radius: 24px;
    font-size: 18px;
    min-width: 48px;
    max-width: 48px;
    min-height: 48px;
    max-height: 48px;
}

#MicButton:hover {
    background-color: #00e6e0;
}

#MicButton[recording="true"] {
    background-color: #e84393;
}

#StopButton {
    background-color: #d63031;
}

#StopButton:hover {
    background-color: #ef4444;
}

#ClearButton {
    background-color: #2a2a45;
}

#ClearButton:hover {
    background-color: #3a3a55;
}

#SidePanel {
    background-color: #15152a;
    border: 1px solid #2a2a45;
    border-radius: 10px;
    padding: 12px;
}

#StatLabel {
    font-size: 12px;
    color: #a0a0c0;
    padding: 4px 0;
}

#StatValue {
    font-size: 18px;
    font-weight: 700;
    color: #8b7cf6;
}

#SectionLabel {
    font-size: 12px;
    font-weight: 700;
    color: #6c5ce7;
    text-transform: uppercase;
    padding-top: 10px;
    padding-bottom: 4px;
}

QScrollBar:vertical {
    background: #15152a;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #3a3a55;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #6c5ce7;
}
"""
