import sys
from dotenv import load_dotenv
load_dotenv()

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NOVA")
    app.setQuitOnLastWindowClosed(False)  # keep running in tray

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
