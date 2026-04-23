from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.compositor import (
    CropBox,
    IDENTITY_TRANSFORM,
    LayerTransform,
    batch_composite,
)


class CompositeWorker(QThread):
    progress = Signal(int, int, str)  # current, total, output_path
    frame_progress = Signal(int, int, str)  # frame_current, frame_total, product_name
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
        *,
        background_transform: LayerTransform = IDENTITY_TRANSFORM,
        foreground_transform: LayerTransform = IDENTITY_TRANSFORM,
        product_transforms: dict[Path, LayerTransform] | None = None,
    ):
        super().__init__()
        self.preset_id = preset_id
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.background_path = background_path
        self.foreground_path = foreground_path
        self.background_crop_box = background_crop_box
        self.foreground_crop_box = foreground_crop_box
        self.background_transform = background_transform
        self.foreground_transform = foreground_transform
        self.product_transforms = product_transforms or {}
        self._cancelled = False

    def run(self):
        try:
            def on_frame(current: int, total: int, name: str) -> None:
                self.frame_progress.emit(current, total, name)

            def is_cancelled() -> bool:
                return self._cancelled

            for current, total, out_path in batch_composite(
                self.preset_id,
                self.input_dir,
                self.output_dir,
                self.background_path,
                self.foreground_path,
                self.background_crop_box,
                self.foreground_crop_box,
                background_transform=self.background_transform,
                foreground_transform=self.foreground_transform,
                product_transforms=self.product_transforms,
                frame_progress=on_frame,
                cancel_check=is_cancelled,
            ):
                self.progress.emit(current, total, str(out_path))
                if self._cancelled:
                    self.cancelled.emit()
                    return
            if self._cancelled:
                self.cancelled.emit()
            else:
                self.completed.emit()
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True
