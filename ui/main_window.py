from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
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

from core.compositor import build_composite, list_products
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
        lbl.setFixedWidth(90)
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
        self.setMinimumSize(720, 600)

        self._worker: CompositeWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # --- Path selectors ---
        self.frame_row = PathRow("框架圖片：", "選擇檔案...")
        self.input_row = PathRow("商品資料夾：", "選擇資料夾...")
        self.output_row = PathRow("輸出資料夾：", "選擇資料夾...")

        layout.addWidget(self.frame_row)
        layout.addWidget(self.input_row)
        layout.addWidget(self.output_row)

        # --- Adjustment panel ---
        self.adjust_group = self._build_adjust_panel()
        layout.addWidget(self.adjust_group)

        # --- Preview ---
        self.preview_label = QLabel("選擇框架圖片與商品資料夾後，將自動預覽合成結果")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px;")
        layout.addWidget(self.preview_label, 1)

        # --- Progress bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)

        # --- Start button ---
        self.start_button = QPushButton("開始套框")
        self.start_button.setFixedHeight(40)
        self.start_button.setEnabled(False)
        layout.addWidget(self.start_button)

        # --- Preview debounce timer ---
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(40)
        self._preview_timer.timeout.connect(self._update_preview)

        # --- Connections ---
        self.frame_row.button.clicked.connect(self._browse_frame)
        self.input_row.button.clicked.connect(self._browse_input)
        self.output_row.button.clicked.connect(self._browse_output)
        self.start_button.clicked.connect(self._on_start_clicked)

    # --- Adjustment panel ---

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

    def _current_adjust(self) -> tuple[int, int, float]:
        return (
            self.offset_x_slider.value(),
            self.offset_y_slider.value(),
            self.scale_slider.value() / 100.0,
        )

    def _schedule_preview(self):
        if self.frame_row.text() and self.input_row.text():
            self._preview_timer.start()

    # --- Browse handlers ---

    def _browse_frame(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇框架圖片", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.frame_row.set_text(path)
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

    # --- State management ---

    def _update_state(self):
        frame_ok = bool(self.frame_row.text())
        input_ok = bool(self.input_row.text())
        output_ok = bool(self.output_row.text())
        self.start_button.setEnabled(frame_ok and input_ok and output_ok)

        if frame_ok and input_ok:
            self._update_preview()

    def _update_preview(self):
        frame_path = Path(self.frame_row.text())
        input_dir = Path(self.input_row.text())

        products = list_products(input_dir)
        if not products:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("資料夾內沒有找到圖片檔案")
            return

        try:
            frame = Image.open(frame_path).convert("RGBA")
            ox, oy, scale = self._current_adjust()
            composite = build_composite(frame, products[0], ox, oy, scale)
            pixmap = pil_to_qpixmap(composite)
            scaled = pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_label.setPixmap(scaled)
        except Exception as e:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"預覽失敗：{e}")

    # --- Batch processing ---

    def _on_start_clicked(self):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            return

        frame_path = Path(self.frame_row.text())
        input_dir = Path(self.input_row.text())
        output_dir = Path(self.output_row.text())

        products = list_products(input_dir)
        if not products:
            QMessageBox.warning(self, "警告", "商品資料夾內沒有圖片檔案。")
            return

        self._set_processing(True, len(products))

        ox, oy, scale = self._current_adjust()
        self._worker = CompositeWorker(frame_path, input_dir, output_dir, ox, oy, scale)
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _set_processing(self, running: bool, total: int = 0):
        self.frame_row.setEnabled(not running)
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
        else:
            self.start_button.setText("開始套框")

    def _on_progress(self, current: int, total: int, output_path: str):
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"處理中 {current}/{total}...")

    def _on_finished(self):
        total = self.progress_bar.maximum()
        self._set_processing(False)
        output_dir = self.output_row.text()
        QMessageBox.information(
            self, "完成", f"已完成 {total} 張圖片套框！\n輸出位置：{output_dir}"
        )

    def _on_error(self, message: str):
        self._set_processing(False)
        QMessageBox.critical(self, "錯誤", f"處理時發生錯誤：\n{message}")

    # --- Resize handling ---

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.frame_row.text() and self.input_row.text():
            self._update_preview()
