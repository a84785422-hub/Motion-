import sys
from PyQt6.QtWidgets import QApplication
from app.gui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Video Motion Control")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
