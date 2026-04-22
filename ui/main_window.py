from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.compositor import (
    CropBox,
    PRESET_ORDER,
    aspect_ratio_matches,
    build_composite,
    build_layer_preview,
    get_layout_preset,
    list_products,
    load_layers,
)
from ui import theme
from ui.crop_dialog import CropDialog
from ui.preview import PreviewPane
from ui.widgets import (
    ActionButton,
    IconLabel,
    PathRow,
    PresetButton,
    SectionHeader,
    SliderRow,
)
from ui.worker import CompositeWorker


SIDEBAR_WIDTH = 408  # +20% from 340
WINDOW_MIN_SIZE = (1108, 680)


def pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    rgba = pil_image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, rgba.width, rgba.height, 4 * rgba.width, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimage)


PRESET_SUBLABEL = {
    "1:1": "1080×1080",
    "9:16": "1080×1920",
    "16:9": "1920×1080",
    "3:4": "1080×1440",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("xFRAME808")
        self.setMinimumSize(*WINDOW_MIN_SIZE)

        self._worker: CompositeWorker | None = None
        self._current_preset_id = PRESET_ORDER[0]
        self._layer_cache_key: tuple[str, str, str, str, str] | None = None
        self._layer_cache: tuple[Image.Image | None, Image.Image | None] | None = None
        self._layer_crops: dict[str, dict[str, CropBox]] = {
            "background": {},
            "foreground": {},
        }

        central = QWidget()
        central.setStyleSheet(f"background: {theme.BG_BASE};")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar(), 0)
        self._preview = PreviewPane()
        root.addWidget(self._preview, 1)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(40)
        self._preview_timer.timeout.connect(self._update_preview)

        # Initial state
        self._apply_preset_to_preview()
        self._update_state()

    # ── Sidebar construction ────────────────────────────────────────────
    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(SIDEBAR_WIDTH)
        side.setStyleSheet(
            f"#Sidebar {{ background: {theme.BG_PANEL}; border-right: 1px solid {theme.BORDER}; }}"
        )

        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Scrollable section area ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setStyleSheet(f"background: {theme.BG_PANEL};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 14, 14, 0)
        content_layout.setSpacing(0)

        content_layout.addWidget(self._build_ratio_section())
        content_layout.addWidget(self._divider())
        content_layout.addWidget(self._build_layers_section())
        content_layout.addWidget(self._divider())
        content_layout.addWidget(self._build_folders_section())
        content_layout.addWidget(self._divider())
        content_layout.addWidget(self._build_adjust_section())
        content_layout.addStretch(1)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # ── Sticky bottom ──
        layout.addWidget(self._build_bottom())

        return side

    def _divider(self) -> QWidget:
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {theme.BORDER};")
        wrap = QWidget()
        wrap_layout = QVBoxLayout(wrap)
        wrap_layout.setContentsMargins(0, 0, 0, 18)
        wrap_layout.addWidget(line)
        return wrap

    def _build_ratio_section(self) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 18)
        v.setSpacing(0)

        v.addWidget(SectionHeader("zap", "輸出比例", "Ratio"))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 0, 0, 0)
        self._preset_button_refs: dict[str, PresetButton] = {}
        for preset_id in PRESET_ORDER:
            btn = PresetButton(preset_id, PRESET_SUBLABEL[preset_id])
            btn.clicked.connect(lambda pid=preset_id: self._on_preset_selected(pid))
            self._preset_button_refs[preset_id] = btn
            btn_row.addWidget(btn)
        self._preset_button_refs[self._current_preset_id].setChecked(True)

        btn_wrap = QWidget()
        btn_wrap.setLayout(btn_row)
        v.addWidget(btn_wrap)

        # Hint pill
        mono = theme.mono_family()
        hint = QWidget()
        hint_row = QHBoxLayout(hint)
        hint_row.setContentsMargins(10, 6, 10, 6)
        hint_row.setSpacing(6)
        hint.setStyleSheet(
            f"background: {theme.BG_ELEVATED}; border: 1px solid {theme.BORDER}; border-radius: {theme.RADIUS_SM}px;"
        )
        hint_row.addWidget(IconLabel("zap", size=9, color=theme.TEXT_MUTED))
        self._hint_label = QLabel("")
        self._hint_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-family: '{mono}'; font-size: 10px; background: transparent; border: none;"
        )
        hint_row.addWidget(self._hint_label)
        hint_row.addStretch(1)

        hint_wrap = QWidget()
        hw = QVBoxLayout(hint_wrap)
        hw.setContentsMargins(0, 7, 0, 0)
        hw.addWidget(hint)
        v.addWidget(hint_wrap)

        self._refresh_hint()
        return container

    def _build_layers_section(self) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 18)
        v.setSpacing(12)

        v.addWidget(SectionHeader("layers", "圖層", "Layers"))

        self._bg_row = PathRow("image", "後景底圖", "Background", show_crop=True, show_clear=True)
        self._fg_row = PathRow("image", "前景套框", "Foreground", show_crop=True, show_clear=True)
        self._bg_row.browse_requested.connect(self._browse_background)
        self._bg_row.crop_requested.connect(self._crop_background)
        self._bg_row.clear_requested.connect(self._clear_background)
        self._fg_row.browse_requested.connect(self._browse_foreground)
        self._fg_row.crop_requested.connect(self._crop_foreground)
        self._fg_row.clear_requested.connect(self._clear_foreground)
        v.addWidget(self._bg_row)
        v.addWidget(self._fg_row)
        return container

    def _build_folders_section(self) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 18)
        v.setSpacing(12)

        v.addWidget(SectionHeader("folder", "資料夾", "Folders"))

        self._input_row = PathRow("folder", "商品資料夾", "Products")
        self._output_row = PathRow("folder", "輸出資料夾", "Output")
        self._input_row.browse_requested.connect(self._browse_input)
        self._output_row.browse_requested.connect(self._browse_output)
        v.addWidget(self._input_row)
        v.addWidget(self._output_row)
        return container

    def _build_adjust_section(self) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 18)
        v.setSpacing(14)

        reset_btn = QPushButton("重置  Reset")
        reset_btn.setFixedHeight(28)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {theme.BG_ELEVATED};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM}px;
                color: {theme.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 500;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {theme.BG_HOVER};
                border-color: {theme.BORDER_STRONG};
                color: {theme.TEXT_PRIMARY};
            }}
            """
        )
        reset_btn.clicked.connect(self._on_reset_adjust)
        v.addWidget(SectionHeader("sliders", "位置微調", "Adjust", action=reset_btn))

        self._offset_x = SliderRow("X 位移", "Offset X", -300, 300, 0, lambda v: f"{'+' if v > 0 else ''}{v}px")
        self._offset_y = SliderRow("Y 位移", "Offset Y", -300, 300, 0, lambda v: f"{'+' if v > 0 else ''}{v}px")
        self._scale = SliderRow("縮放", "Scale", 50, 150, 100, lambda v: f"{v}%")

        self._offset_x.value_changed.connect(lambda _: self._schedule_preview())
        self._offset_y.value_changed.connect(lambda _: self._schedule_preview())
        self._scale.value_changed.connect(lambda _: self._schedule_preview())

        v.addWidget(self._offset_x)
        v.addWidget(self._offset_y)
        v.addWidget(self._scale)
        return container

    def _build_bottom(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet(
            f"QFrame {{ background: {theme.BG_PANEL}; border-top: 1px solid {theme.BORDER}; }}"
        )
        v = QVBoxLayout(container)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        # Status pill (success)
        self._status_pill = QFrame()
        self._status_pill.setStyleSheet(
            f"""
            QFrame {{
                background: {theme.SUCCESS_GLOW};
                border: 1px solid {theme.SUCCESS_BORDER};
                border-radius: {theme.RADIUS_SM}px;
            }}
            """
        )
        pill_row = QHBoxLayout(self._status_pill)
        pill_row.setContentsMargins(10, 7, 10, 7)
        pill_row.setSpacing(8)
        check_icon = IconLabel("check", size=10, color=theme.SUCCESS)
        check_icon.setStyleSheet("background: transparent;")
        pill_row.addWidget(check_icon)
        self._status_pill_label = QLabel("")
        self._status_pill_label.setStyleSheet(
            f"color: {theme.SUCCESS}; font-size: 11px; font-weight: 500; background: transparent; border: none;"
        )
        pill_row.addWidget(self._status_pill_label)
        pill_row.addStretch(1)
        self._status_pill.setVisible(False)
        v.addWidget(self._status_pill)

        # Progress block
        self._progress_box = QWidget()
        self._progress_box.setStyleSheet("background: transparent;")
        pbl = QVBoxLayout(self._progress_box)
        pbl.setContentsMargins(0, 0, 0, 0)
        pbl.setSpacing(5)
        prog_row = QHBoxLayout()
        prog_row.setContentsMargins(0, 0, 0, 0)
        prog_label_zh = QLabel("處理中…")
        prog_label_zh.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        prog_row.addWidget(prog_label_zh)
        prog_row.addStretch(1)
        mono = theme.mono_family()
        self._progress_count = QLabel("0/0")
        self._progress_count.setStyleSheet(
            f"color: {theme.TEXT_SECONDARY}; font-family: '{mono}'; font-size: 11px;"
        )
        prog_row.addWidget(self._progress_count)
        pbl.addLayout(prog_row)

        self._progress_track = QFrame()
        self._progress_track.setFixedHeight(3)
        self._progress_track.setStyleSheet(
            f"background: {theme.BG_ACTIVE}; border-radius: 2px;"
        )
        self._progress_fill = QFrame(self._progress_track)
        self._progress_fill.setStyleSheet(f"background: {theme.ACCENT}; border-radius: 2px;")
        self._progress_fill.setGeometry(0, 0, 0, 3)
        pbl.addWidget(self._progress_track)
        self._progress_box.setVisible(False)
        v.addWidget(self._progress_box)

        # Main action
        self._action_btn = ActionButton()
        self._action_btn.clicked.connect(self._on_start_clicked)
        v.addWidget(self._action_btn)

        return container

    # ── Helpers ─────────────────────────────────────────────────────────
    def _refresh_hint(self) -> None:
        preset = get_layout_preset(self._current_preset_id)
        w, h = preset.canvas_size
        self._hint_label.setText(f"{w} × {h} px  ·  白底輸出  ·  WHITE FLATTEN")

    def _apply_preset_to_preview(self) -> None:
        preset = get_layout_preset(self._current_preset_id)
        self._preview.set_preset(self._current_preset_id, preset.canvas_size)

    def _current_adjust(self) -> tuple[int, int, float]:
        return (self._offset_x.value(), self._offset_y.value(), self._scale.value() / 100.0)

    def _has_selected_layers(self) -> bool:
        return bool(self._bg_row.text() or self._fg_row.text())

    def _layer_row(self, layer_key: str) -> PathRow:
        return self._bg_row if layer_key == "background" else self._fg_row

    def _layer_label(self, layer_key: str) -> str:
        return "後景底圖" if layer_key == "background" else "前景套框"

    def _current_layer_crop(self, layer_key: str) -> CropBox | None:
        return self._layer_crops[layer_key].get(self._current_preset_id)

    def _selected_layer_specs(self) -> tuple[Path | None, CropBox | None, Path | None, CropBox | None]:
        bg = Path(self._bg_row.text()) if self._bg_row.text() else None
        fg = Path(self._fg_row.text()) if self._fg_row.text() else None
        return bg, self._current_layer_crop("background"), fg, self._current_layer_crop("foreground")

    def _refresh_layer_row_state(self, layer_key: str) -> None:
        self._layer_row(layer_key).set_cropped(self._current_layer_crop(layer_key) is not None)

    def _set_layer_selection(self, layer_key: str, path: Path, crop_box: CropBox | None = None) -> None:
        row = self._layer_row(layer_key)
        row.set_text(str(path))
        self._layer_crops[layer_key].clear()
        if crop_box is not None:
            self._layer_crops[layer_key][self._current_preset_id] = crop_box
        self._refresh_layer_row_state(layer_key)

    def _clear_layer_selection(self, layer_key: str) -> None:
        self._layer_row(layer_key).clear()
        self._layer_crops[layer_key].clear()
        self._refresh_layer_row_state(layer_key)

    def _normalize_crop_box(self, path: Path, crop_box: CropBox) -> CropBox | None:
        with Image.open(path) as image:
            full_box = (0, 0, image.width, image.height)
            preset = get_layout_preset(self._current_preset_id)
            if crop_box == full_box and aspect_ratio_matches(image.size, preset):
                return None
        return crop_box

    def _image_requires_crop(self, path: Path) -> bool:
        preset = get_layout_preset(self._current_preset_id)
        with Image.open(path) as image:
            return not aspect_ratio_matches(image.size, preset)

    def _run_crop_dialog(
        self,
        layer_key: str,
        path: Path,
        initial_crop_box: CropBox | None,
    ) -> tuple[bool, CropBox | None]:
        dialog = CropDialog(
            path,
            self._layer_label(layer_key),
            self._current_preset_id,
            get_layout_preset(self._current_preset_id).canvas_size,
            initial_crop_box=initial_crop_box,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False, None
        return True, self._normalize_crop_box(path, dialog.crop_box())

    def _select_layer_file(self, layer_key: str, title: str) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, title, "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not path_str:
            return

        path = Path(path_str)
        try:
            crop_box = None
            if self._image_requires_crop(path):
                accepted, crop_box = self._run_crop_dialog(layer_key, path, None)
                if not accepted:
                    return
            self._set_layer_selection(layer_key, path, crop_box)
            self._invalidate_layer_cache()
            self._update_state()
        except Exception as exc:
            QMessageBox.warning(self, "警告", str(exc))

    def _edit_layer_crop(self, layer_key: str) -> None:
        row = self._layer_row(layer_key)
        if not row.text():
            return
        path = Path(row.text())
        try:
            accepted, crop_box = self._run_crop_dialog(layer_key, path, self._current_layer_crop(layer_key))
            if not accepted:
                return
            if crop_box is None:
                self._layer_crops[layer_key].pop(self._current_preset_id, None)
            else:
                self._layer_crops[layer_key][self._current_preset_id] = crop_box
            self._refresh_layer_row_state(layer_key)
            self._invalidate_layer_cache()
            self._update_state()
        except Exception as exc:
            QMessageBox.warning(self, "警告", str(exc))

    def _invalidate_layer_cache(self) -> None:
        self._layer_cache_key = None
        self._layer_cache = None

    def _get_loaded_layers(self) -> tuple[Image.Image | None, Image.Image | None]:
        bg, bg_crop, fg, fg_crop = self._selected_layer_specs()
        key = (self._current_preset_id, str(bg or ""), str(bg_crop or ""), str(fg or ""), str(fg_crop or ""))
        if key != self._layer_cache_key:
            self._layer_cache = load_layers(
                self._current_preset_id,
                background_path=bg,
                foreground_path=fg,
                background_crop_box=bg_crop,
                foreground_crop_box=fg_crop,
            )
            self._layer_cache_key = key
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

    # ── Actions ─────────────────────────────────────────────────────────
    def _on_preset_selected(self, preset_id: str) -> None:
        self._current_preset_id = preset_id
        # Enforce exclusivity — PresetButton is not a QAbstractButton, so we
        # do this manually instead of via QButtonGroup.
        for pid, btn in self._preset_button_refs.items():
            btn.setChecked(pid == preset_id)
        self._refresh_hint()
        self._apply_preset_to_preview()
        self._refresh_layer_row_state("background")
        self._refresh_layer_row_state("foreground")
        self._invalidate_layer_cache()
        self._update_state()

    def _on_reset_adjust(self) -> None:
        self._offset_x.set_value(0)
        self._offset_y.set_value(0)
        self._scale.set_value(100)

    def _schedule_preview(self) -> None:
        if self._has_selected_layers():
            self._preview_timer.start()

    def _browse_background(self) -> None:
        self._select_layer_file("background", "選擇後景底圖")

    def _browse_foreground(self) -> None:
        self._select_layer_file("foreground", "選擇前景套框")

    def _crop_background(self) -> None:
        self._edit_layer_crop("background")

    def _crop_foreground(self) -> None:
        self._edit_layer_crop("foreground")

    def _clear_background(self) -> None:
        self._clear_layer_selection("background")
        self._invalidate_layer_cache()
        self._update_state()

    def _clear_foreground(self) -> None:
        self._clear_layer_selection("foreground")
        self._invalidate_layer_cache()
        self._update_state()

    def _browse_input(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "選擇商品資料夾")
        if path:
            self._input_row.set_text(path)
            self._update_state()

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if path:
            self._output_row.set_text(path)
            self._update_state()

    def _update_state(self) -> None:
        has_layers = self._has_selected_layers()
        input_ok = bool(self._input_row.text())
        output_ok = bool(self._output_row.text())
        layer_error = self._validate_layers() if has_layers else None
        running = self._worker is not None and self._worker.isRunning()

        if not running:
            can_start = has_layers and input_ok and output_ok and layer_error is None
            self._action_btn.set_mode(ActionButton.MODE_IDLE, enabled=can_start)

        if has_layers:
            self._update_preview()
        elif input_ok and not has_layers:
            self._preview.set_status("請至少選擇前景套框或後景底圖。")
        else:
            self._preview.set_status("選擇輸出比例與圖層後\n自動顯示合成預覽")

    def _update_preview(self) -> None:
        if not self._has_selected_layers():
            self._preview.set_status("請至少選擇前景套框或後景底圖。")
            return

        try:
            background, foreground = self._get_loaded_layers()
            if self._input_row.text():
                input_dir = Path(self._input_row.text())
                products = list_products(input_dir)
                if not products:
                    self._preview.set_status("資料夾內沒有找到圖片檔案", error=True)
                    return
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
            else:
                composite = build_layer_preview(
                    self._current_preset_id,
                    background=background,
                    foreground=foreground,
                )
            self._preview.set_pixmap(pil_to_qpixmap(composite))
        except Exception as exc:
            self._preview.set_status(f"預覽失敗\n{exc}", error=True)

    def _on_start_clicked(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            return

        if not self._input_row.text():
            QMessageBox.warning(self, "警告", "請先選擇商品資料夾。")
            return
        if not self._output_row.text():
            QMessageBox.warning(self, "警告", "請先選擇輸出資料夾。")
            return

        bg, bg_crop, fg, fg_crop = self._selected_layer_specs()
        if bg is None and fg is None:
            QMessageBox.warning(self, "警告", "請至少選擇前景套框或後景底圖。")
            return

        input_dir = Path(self._input_row.text())
        output_dir = Path(self._output_row.text())
        products = list_products(input_dir)
        if not products:
            QMessageBox.warning(self, "警告", "商品資料夾內沒有圖片檔案。")
            return

        layer_error = self._validate_layers()
        if layer_error is not None:
            QMessageBox.warning(self, "警告", layer_error)
            return

        self._status_pill.setVisible(False)
        self._set_processing(True, len(products))

        ox, oy, scale = self._current_adjust()
        self._worker = CompositeWorker(
            self._current_preset_id,
            input_dir,
            output_dir,
            background_path=bg,
            foreground_path=fg,
            background_crop_box=bg_crop,
            foreground_crop_box=fg_crop,
            offset_x=ox,
            offset_y=oy,
            scale=scale,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_finished)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _set_processing(self, running: bool, total: int = 0) -> None:
        # Disable inputs (not the action button)
        for w in (self._bg_row, self._fg_row, self._input_row, self._output_row,
                  self._offset_x, self._offset_y, self._scale):
            w.setEnabled(not running)
        for btn in self._preset_button_refs.values():
            btn.setEnabled(not running)

        self._progress_box.setVisible(running)
        if running:
            self._progress_total = total
            self._progress_count.setText(f"0/{total}")
            self._update_progress_fill(0, total)
            self._action_btn.set_mode(ActionButton.MODE_RUNNING, enabled=True)
        else:
            self._progress_total = 0
            self._update_state()

    def _update_progress_fill(self, current: int, total: int) -> None:
        track_w = max(1, self._progress_track.width())
        ratio = (current / total) if total else 0
        self._progress_fill.setGeometry(0, 0, int(track_w * ratio), 3)

    def _on_progress(self, current: int, total: int, output_path: str) -> None:
        self._progress_count.setText(f"{current}/{total}")
        self._update_progress_fill(current, total)

    def _on_finished(self) -> None:
        total = getattr(self, "_progress_total", 0)
        self._set_processing(False)
        self._status_pill_label.setText(f"完成！{total} 張已輸出")
        self._status_pill.setVisible(True)
        output_dir = self._output_row.text()
        QMessageBox.information(self, "完成", f"已完成 {total} 張圖片套框！\n輸出位置：{output_dir}")

    def _on_cancelled(self) -> None:
        # Grab completed count before resetting progress widgets.
        try:
            current = int(self._progress_count.text().split("/")[0])
        except Exception:
            current = 0
        total = getattr(self, "_progress_total", 0)
        self._set_processing(False)
        QMessageBox.information(self, "已取消", f"已取消處理，目前已完成 {current}/{total} 張圖片。")

    def _on_error(self, message: str) -> None:
        self._set_processing(False)
        QMessageBox.critical(self, "錯誤", f"處理時發生錯誤：\n{message}")

    # ── Events ──────────────────────────────────────────────────────────
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._has_selected_layers():
            self._update_preview()
        # Re-fit the progress bar fill on resize
        if self._progress_box.isVisible():
            try:
                cur, total = self._progress_count.text().split("/")
                self._update_progress_fill(int(cur), int(total))
            except Exception:
                pass
