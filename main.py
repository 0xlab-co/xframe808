import os
import subprocess
import sys

from PySide6.QtWidgets import QApplication

from ui import theme
from ui.main_window import MainWindow


def _strip_macos_quarantine() -> None:
    """Remove com.apple.quarantine from bundled binaries on frozen macOS builds.

    Without this, users who unzip our unsigned .app from Safari and launch via
    Gatekeeper's "Open Anyway" will still have quarantine flags on nested
    executables (ffmpeg, etc.). macOS silently kills quarantined nested
    binaries when the parent process spawns them, which breaks video output.

    The app has permission to xattr its own bundle when installed outside
    /Applications. We best-effort the call and swallow failures.
    """
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return
    try:
        exe = os.path.realpath(sys.executable)
        # sys.executable for a PyInstaller .app is .../xFRAME808.app/Contents/MacOS/xFRAME808
        contents = os.path.dirname(os.path.dirname(exe))
        bundle = os.path.dirname(contents)
        if bundle.endswith(".app"):
            subprocess.run(
                ["xattr", "-dr", "com.apple.quarantine", bundle],
                check=False,
                capture_output=True,
                timeout=5,
            )
    except Exception:
        # Non-fatal; user can still strip manually via README instructions.
        pass


def main():
    _strip_macos_quarantine()
    app = QApplication(sys.argv)
    app.setApplicationName("xFRAME808")
    app.setStyleSheet(theme.build_global_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
