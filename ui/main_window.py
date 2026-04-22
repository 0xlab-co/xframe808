from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.compositor import PRESET_ORDER, build_composite, get_layout_preset, list_products, load_layers
from ui.worker import CompositeWorker


def pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    rgba = pil_image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, rgba.width, rgba.height, 4 * rgba.width, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimage)


class PathRow(QWidget):
    def __init__(self, label: str, button_text: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        lbl.setFixedWidth(100)
        self.line_edit = QLineEdit()
        self.line_edit.setReadOnly(True)
        self.button = QPushButton(button_text)
        self.button.setFixedWidth(110)

        layout.addWidget(lbl)
        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.button)

    def text(self) -> str:
        return self.line_edit.text()

    def set_text(self, text: str) -> None:
        self.line_edit.setText(text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("xFRAME808")
        self.setMinimumSize(780, 640)

        self._worker: CompositeWorker | None = None
        self._current_preset_id = PRESET_ORDER[0]
        self._layer_cache_key: tuple[str, str, str] | None = None
        self._layer_cache: tuple[Image.Image | None, Image.Image | None] | None = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self.preset_group = self._build_preset_panel()
        layout.addWidget(self.preset_group)

        self.background_row = PathRow("後景底圖：", "選擇檔案...")
        self.foreground_row = PathRow("前景套框：", "選擇檔案...")
        self.input_row = PathRow("商品資料夾：", "選擇資料夾...")
        self.output_row = PathRow("輸出資料夾：", "選擇資料夾...")

        layout.addWidget(self.background_row)
        layout.addWidget(self.foreground_row)
        layout.addWidget(self.input_row)
        layout.addWidget(self.output_row)

        self.adjust_group = self._build_adjust_panel()
        layout.addWidget(self.adjust_group)

        self.preview_label = QLabel("選擇輸出比例、至少一個景圖與商品資料夾後，將自動預覽白底輸出結果")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px;")
        layout.addWidget(self.preview_label, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)

        self.start_button = QPushButton("開始套框")
        self.start_button.setFixedHeight(40)
        self.start_button.setEnabled(False)
        layout.addWidget(self.start_button)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(40)
        self._preview_timer.timeout.connect(self._update_preview)

        self.background_row.button.clicked.connect(self._browse_background)
        self.foreground_row.button.clicked.connect(self._browse_foreground)
        self.input_row.button.clicked.connect(self._browse_input)
        self.output_row.button.clicked.connect(self._browse_output)
        self.start_button.clicked.connect(self._on_start_clicked)

        self._update_preset_hint()

    def _build_preset_panel(self) -> QGroupBox:
        group = QGroupBox("輸出比例")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.preset_buttons = QButtonGroup(self)
        self.preset_buttons.setExclusive(True)
        self._preset_button_refs: dict[str, QPushButton] = {}

        for preset_id in PRESET_ORDER:
            button = QPushButton(preset_id)
            button.setCheckable(True)
            button.setMinimumHeight(34)
            button.setStyleSheet(
                "QPushButton:checked { background-color: #1f6feb; color: white; border-color: #1f6feb; }"
            )
            button.clicked.connect(lambda checked, value=preset_id: self._on_preset_selected(value))
            self.preset_buttons.addButton(button)
            self._preset_button_refs[preset_id] = button
            button_row.addWidget(button)

        self._preset_button_refs[self._current_preset_id].setChecked(True)
        self.preset_hint = QLabel("")
        self.preset_hint.setStyleSheet("color: #666;")

        layout.addLayout(button_row)
        layout.addWidget(self.preset_hint)
        return group

    def _build_adjust_panel(self) -> QGroupBox:
        group = QGroupBox("位置微調")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        def make_row(row: int, label_text: str, minimum: int, maximum: int, default: int, suffix: str):
            lbl = QLabel(label_text)
            lbl.setFixedWidth(70)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(minimum)
            slider.setMaximum(maximum)
            slider.setValue(default)
            value_lbl = QLabel(f"{default}{suffix}")
            value_lbl.setFixedWidth(70)
            value_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(slider, row, 1)
            grid.addWidget(value_lbl, row, 2)
            return slider, value_lbl

        self.offset_x_slider, self.offset_x_value = make_row(0, "X 位移：", -300, 300, 0, " px")
        self.offset_y_slider, self.offset_y_value = make_row(1, "Y 位移：", -300, 300, 0, " px")
        self.scale_slider, self.scale_value = make_row(2, "縮放：", 50, 150, 100, " %")

        self.reset_button = QPushButton("重置")
        self.reset_button.setFixedWidth(80)
        grid.addWidget(self.reset_button, 3, 2)

        self.offset_x_slider.valueChanged.connect(self._on_offset_x_changed)
        self.offset_y_slider.valueChanged.connect(self._on_offset_y_changed)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        self.reset_button.clicked.connect(self._on_reset_adjust)

        return group

    def _current_adjust(self) -> tuple[int, int, float]:
        return (
            self.offset_x_slider.value(),
            self.offset_y_slider.value(),
            self.scale_slider.value() / 100.0,
        )

    def _has_selected_layers(self) -> bool:
        return bool(self.background_row.text() or self.foreground_row.text())

    def _selected_layer_paths(self) -> tuple[Path | None, Path | None]:
        background_path = Path(self.background_row.text()) if self.background_row.text() else None
        foreground_path = Path(self.foreground_row.text()) if self.foreground_row.text() else None
        return background_path, foreground_path

    def _invalidate_layer_cache(self) -> None:
        self._layer_cache_key = None
        self._layer_cache = None

    def _get_loaded_layers(self) -> tuple[Image.Image | None, Image.Image | None]:
        background_path, foreground_path = self._selected_layer_paths()
        cache_key = (
            self._current_preset_id,
            str(background_path or ""),
            str(foreground_path or ""),
        )
        if cache_key != self._layer_cache_key:
            self._layer_cache = load_layers(
                self._current_preset_id,
                background_path=background_path,
                foreground_path=foreground_path,
            )
            self._layer_cache_key = cache_key
        assert self._layer_cache is not None
        return self._layer_cache

    def _validate_layers(self) -> str | None:
        if not self._has_selected_layers():
            return "請至少選擇前景套框或後景底圖。"
        try:
            self._get_loaded_layers()
        except Exception as exc:
            return str(exc)
        return None

    def _set_preview_text(self, message: str) -> None:
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(message)

    def _update_preset_hint(self) -> None:
        preset = get_layout_preset(self._current_preset_id)
        width, height = preset.canvas_size
        self.preset_hint.setText(
            f"固定輸出畫布：{preset.preset_id} ({width} x {height}) | 前景白底可自動處理，輸出固定補白底"
        )

    def _on_preset_selected(self, preset_id: str) -> None:
        self._current_preset_id = preset_id
        self._update_preset_hint()
        self._invalidate_layer_cache()
        self._update_state()

    def _on_offset_x_changed(self, value: int):
        self.offset_x_value.setText(f"{value} px")
        self._schedule_preview()

    def _on_offset_y_changed(self, value: int):
        self.offset_y_value.setText(f"{value} px")
        self._schedule_preview()

    def _on_scale_changed(self, value: int):
        self.scale_value.setText(f"{value} %")
        self._schedule_preview()

    def _on_reset_adjust(self):
        self.offset_x_slider.setValue(0)
        self.offset_y_slider.setValue(0)
        self.scale_slider.setValue(100)

    def _schedule_preview(self):
        if self._has_selected_layers() and self.input_row.text():
            self._preview_timer.start()

    def _browse_background(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇後景底圖", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.background_row.set_text(path)
            self._invalidate_layer_cache()
            self._update_state()

    def _browse_foreground(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇前景套框", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.foreground_row.set_text(path)
            self._invalidate_layer_cache()
            self._update_state()

    def _browse_input(self):
        path = QFileDialog.getExistingDirectory(self, "選擇商品資料夾")
        if path:
            self.input_row.set_text(path)
            self._update_state()

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if path:
            self.output_row.set_text(path)
            self._update_state()

    def _update_state(self):
        has_layers = self._has_selected_layers()
        input_ok = bool(self.input_row.text())
        output_ok = bool(self.output_row.text())
        layer_error = self._validate_layers() if has_layers else None

        if self._worker is None or not self._worker.isRunning():
            self.start_button.setEnabled(has_layers and input_ok and output_ok and layer_error is None)

        if has_layers and input_ok:
            self._update_preview()
        elif layer_error:
            self._set_preview_text(f"預覽失敗：{layer_error}")
        elif input_ok and not has_layers:
            self._set_preview_text("請至少選擇前景套框或後景底圖。")
        else:
            self._set_preview_text("選擇輸出比例、至少一個景圖與商品資料夾後，將自動預覽白底輸出結果")

    def _update_preview(self):
        if not self.input_row.text():
            self._set_preview_text("選擇商品資料夾後，將自動預覽白底輸出結果")
            return
        if not self._has_selected_layers():
            self._set_preview_text("請至少選擇前景套框或後景底圖。")
            return

        input_dir = Path(self.input_row.text())
        products = list_products(input_dir)
        if not products:
            self._set_preview_text("資料夾內沒有找到圖片檔案")
            return

        try:
            background, foreground = self._get_loaded_layers()
            ox, oy, scale = self._current_adjust()
            composite = build_composite(
                self._current_preset_id,
                products[0],
                background=background,
                foreground=foreground,
                offset_x=ox,
                offset_y=oy,
                scale=scale,
            )
            pixmap = pil_to_qpixmap(composite)
            scaled = pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_label.setText("")
            self.preview_label.setPixmap(scaled)
        except Exception as exc:
            self._set_preview_text(f"預覽失敗：{exc}")

    def _on_start_clicked(self):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            return

        if not self.input_row.text():
            QMessageBox.warning(self, "警告", "請先選擇商品資料夾。")
            return
        if not self.output_row.text():
            QMessageBox.warning(self, "警告", "請先選擇輸出資料夾。")
            return

        background_path, foreground_path = self._selected_layer_paths()
        if background_path is None and foreground_path is None:
            QMessageBox.warning(self, "警告", "請至少選擇前景套框或後景底圖。")
            return

        input_dir = Path(self.input_row.text())
        output_dir = Path(self.output_row.text())
        products = list_products(input_dir)
        if not products:
            QMessageBox.warning(self, "警告", "商品資料夾內沒有圖片檔案。")
            return

        layer_error = self._validate_layers()
        if layer_error is not None:
            QMessageBox.warning(self, "警告", layer_error)
            return

        self._set_processing(True, len(products))

        ox, oy, scale = self._current_adjust()
        self._worker = CompositeWorker(
            self._current_preset_id,
            input_dir,
            output_dir,
            background_path=background_path,
            foreground_path=foreground_path,
            offset_x=ox,
            offset_y=oy,
            scale=scale,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_finished)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _set_processing(self, running: bool, total: int = 0):
        self.preset_group.setEnabled(not running)
        self.background_row.setEnabled(not running)
        self.foreground_row.setEnabled(not running)
        self.input_row.setEnabled(not running)
        self.output_row.setEnabled(not running)
        self.adjust_group.setEnabled(not running)

        self.progress_bar.setVisible(running)
        self.progress_label.setVisible(running)
        if running:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(0)
            self.progress_label.setText(f"處理中 0/{total}...")
            self.start_button.setText("取消")
            self.start_button.setEnabled(True)
        else:
            self.start_button.setText("開始套框")

    def _on_progress(self, current: int, total: int, output_path: str):
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"處理中 {current}/{total}...")

    def _on_finished(self):
        total = self.progress_bar.maximum()
        self._set_processing(False)
        self._update_state()
        output_dir = self.output_row.text()
        QMessageBox.information(
            self, "完成", f"已完成 {total} 張圖片套框！\n輸出位置：{output_dir}"
        )

    def _on_cancelled(self):
        current = self.progress_bar.value()
        total = self.progress_bar.maximum()
        self._set_processing(False)
        self._update_state()
        QMessageBox.information(self, "已取消", f"已取消處理，目前已完成 {current}/{total} 張圖片。")

    def _on_error(self, message: str):
        self._set_processing(False)
        self._update_state()
        QMessageBox.critical(self, "錯誤", f"處理時發生錯誤：\n{message}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._has_selected_layers() and self.input_row.text():
            self._update_preview()
