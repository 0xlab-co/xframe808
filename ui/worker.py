from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.compositor import CropBox, batch_composite


class CompositeWorker(QThread):
    progress = Signal(int, int, str)  # current, total, output_path
    completed = Signal()
    cancelled = Signal()
    error = Signal(str)

    def __init__(
        self,
        preset_id: str,
        input_dir: Path,
        output_dir: Path,
        background_path: Path | None = None,
        foreground_path: Path | None = None,
        background_crop_box: CropBox | None = None,
        foreground_crop_box: CropBox | None = None,
        offset_x: int = 0,
        offset_y: int = 0,
        scale: float = 1.0,
    ):
        super().__init__()
        self.preset_id = preset_id
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.background_path = background_path
        self.foreground_path = foreground_path
        self.background_crop_box = background_crop_box
        self.foreground_crop_box = foreground_crop_box
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.scale = scale
        self._cancelled = False

    def run(self):
        try:
            for current, total, out_path in batch_composite(
                self.preset_id,
                self.input_dir,
                self.output_dir,
                self.background_path,
                self.foreground_path,
                self.background_crop_box,
                self.foreground_crop_box,
                self.offset_x,
                self.offset_y,
                self.scale,
            ):
                self.progress.emit(current, total, str(out_path))
                if self._cancelled:
                    self.cancelled.emit()
                    return
            self.completed.emit()
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True
