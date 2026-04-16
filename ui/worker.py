from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.compositor import batch_composite


class CompositeWorker(QThread):
    progress = Signal(int, int, str)  # current, total, output_path
    completed = Signal()
    error = Signal(str)

    def __init__(
        self,
        frame_path: Path,
        input_dir: Path,
        output_dir: Path,
        offset_x: int = 0,
        offset_y: int = 0,
        scale: float = 1.0,
    ):
        super().__init__()
        self.frame_path = frame_path
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.scale = scale
        self._cancelled = False

    def run(self):
        try:
            for current, total, out_path in batch_composite(
                self.frame_path,
                self.input_dir,
                self.output_dir,
                self.offset_x,
                self.offset_y,
                self.scale,
            ):
                if self._cancelled:
                    return
                self.progress.emit(current, total, str(out_path))
            self.completed.emit()
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True
