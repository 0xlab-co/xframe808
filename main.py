import sys

from PySide6.QtWidgets import QApplication

from ui import theme
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("xFRAME808")
    app.setStyleSheet(theme.build_global_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
