from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.compositor import CropBox
from ui import theme


class CropCanvas(QWidget):
    changed = Signal()

    _HANDLE_RADIUS = 6.0
    _MIN_EDGE = 24.0

    def __init__(
        self,
        pixmap: QPixmap,
        aspect_ratio: float,
        initial_crop_box: CropBox | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._pixmap = pixmap
        self._aspect_ratio = aspect_ratio
        self._active_mode: str | None = None
        self._move_offset = QPointF()
        self.setMinimumSize(440, 440)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        if initial_crop_box is not None:
            left, top, right, bottom = initial_crop_box
            self._crop_rect = QRectF(left, top, right - left, bottom - top)
            self._crop_rect = self._sanitize_rect(self._crop_rect)
        else:
            self._crop_rect = self._default_crop_rect()

    def _image_bounds(self) -> QRectF:
        return QRectF(0.0, 0.0, float(self._pixmap.width()), float(self._pixmap.height()))

    def _default_crop_rect(self) -> QRectF:
        image_rect = self._image_bounds()
        image_ratio = image_rect.width() / image_rect.height()
        if image_ratio > self._aspect_ratio:
            crop_h = image_rect.height()
            crop_w = crop_h * self._aspect_ratio
        else:
            crop_w = image_rect.width()
            crop_h = crop_w / self._aspect_ratio
        left = (image_rect.width() - crop_w) / 2.0
        top = (image_rect.height() - crop_h) / 2.0
        return QRectF(left, top, crop_w, crop_h)

    def _sanitize_rect(self, rect: QRectF) -> QRectF:
        bounds = self._image_bounds()
        left = max(bounds.left(), min(rect.left(), bounds.right() - 1.0))
        top = max(bounds.top(), min(rect.top(), bounds.bottom() - 1.0))
        right = max(left + 1.0, min(rect.right(), bounds.right()))
        bottom = max(top + 1.0, min(rect.bottom(), bounds.bottom()))
        return QRectF(left, top, right - left, bottom - top)

    def reset_crop(self) -> None:
        self._crop_rect = self._default_crop_rect()
        self.changed.emit()
        self.update()

    def crop_box(self) -> CropBox:
        rect = self._sanitize_rect(self._crop_rect)
        left = int(round(rect.left()))
        top = int(round(rect.top()))
        right = int(round(rect.right()))
        bottom = int(round(rect.bottom()))
        return (left, top, right, bottom)

    def _display_rect(self) -> QRectF:
        padding = 18.0
        avail_w = max(1.0, self.width() - padding * 2.0)
        avail_h = max(1.0, self.height() - padding * 2.0)
        image_ratio = self._pixmap.width() / self._pixmap.height()
        avail_ratio = avail_w / avail_h
        if avail_ratio > image_ratio:
            height = avail_h
            width = height * image_ratio
        else:
            width = avail_w
            height = width / image_ratio
        left = (self.width() - width) / 2.0
        top = (self.height() - height) / 2.0
        return QRectF(left, top, width, height)

    def _image_to_widget_rect(self, rect: QRectF) -> QRectF:
        display = self._display_rect()
        scale = display.width() / self._pixmap.width()
        return QRectF(
            display.left() + rect.left() * scale,
            display.top() + rect.top() * scale,
            rect.width() * scale,
            rect.height() * scale,
        )

    def _widget_to_image_point(self, point: QPointF) -> QPointF:
        display = self._display_rect()
        scale = self._pixmap.width() / display.width()
        x = (point.x() - display.left()) * scale
        y = (point.y() - display.top()) * scale
        return QPointF(
            max(0.0, min(float(self._pixmap.width()), x)),
            max(0.0, min(float(self._pixmap.height()), y)),
        )

    def _handle_points(self) -> dict[str, QPointF]:
        rect = self._image_to_widget_rect(self._crop_rect)
        return {
            "nw": rect.topLeft(),
            "ne": rect.topRight(),
            "sw": rect.bottomLeft(),
            "se": rect.bottomRight(),
        }

    def _handle_at(self, point: QPointF) -> str | None:
        for name, handle in self._handle_points().items():
            if (handle - point).manhattanLength() <= self._HANDLE_RADIUS * 2.2:
                return name
        return None

    def _update_cursor(self, point: QPointF) -> None:
        handle = self._handle_at(point)
        if handle in {"nw", "se"}:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle in {"ne", "sw"}:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif self._image_to_widget_rect(self._crop_rect).contains(point):
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _move_crop_rect(self, point: QPointF) -> None:
        bounds = self._image_bounds()
        width = self._crop_rect.width()
        height = self._crop_rect.height()
        top_left = point - self._move_offset
        left = max(bounds.left(), min(top_left.x(), bounds.right() - width))
        top = max(bounds.top(), min(top_left.y(), bounds.bottom() - height))
        self._crop_rect = QRectF(left, top, width, height)

    def _resize_crop_rect(self, handle: str, point: QPointF) -> None:
        bounds = self._image_bounds()
        anchors = {
            "se": (self._crop_rect.topLeft(), 1.0, 1.0),
            "sw": (self._crop_rect.topRight(), -1.0, 1.0),
            "ne": (self._crop_rect.bottomLeft(), 1.0, -1.0),
            "nw": (self._crop_rect.bottomRight(), -1.0, -1.0),
        }
        anchor, x_sign, y_sign = anchors[handle]
        dx = max(self._MIN_EDGE, (point.x() - anchor.x()) * x_sign)
        dy = max(self._MIN_EDGE, (point.y() - anchor.y()) * y_sign)
        max_dx = anchor.x() if x_sign < 0 else bounds.right() - anchor.x()
        max_dy = anchor.y() if y_sign < 0 else bounds.bottom() - anchor.y()
        dx = min(dx, max_dx)
        dy = min(dy, max_dy)
        if dx / dy > self._aspect_ratio:
            dx = dy * self._aspect_ratio
        else:
            dy = dx / self._aspect_ratio
        left = anchor.x() if x_sign > 0 else anchor.x() - dx
        top = anchor.y() if y_sign > 0 else anchor.y() - dy
        self._crop_rect = QRectF(left, top, dx, dy)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        point = event.position()
        handle = self._handle_at(point)
        if handle is not None:
            self._active_mode = handle
        elif self._image_to_widget_rect(self._crop_rect).contains(point):
            self._active_mode = "move"
            self._move_offset = self._widget_to_image_point(point) - self._crop_rect.topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            self._active_mode = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        point = event.position()
        if self._active_mode == "move":
            self._move_crop_rect(self._widget_to_image_point(point))
            self.changed.emit()
            self.update()
        elif self._active_mode in {"nw", "ne", "sw", "se"}:
            self._resize_crop_rect(self._active_mode, self._widget_to_image_point(point))
            self.changed.emit()
            self.update()
        else:
            self._update_cursor(point)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._active_mode = None
        self._update_cursor(event.position())
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor(theme.BG_BASE))

        display = self._display_rect()
        painter.fillRect(display, QColor(theme.PREVIEW_MATTE))
        painter.drawPixmap(display, self._pixmap, QRectF(0.0, 0.0, float(self._pixmap.width()), float(self._pixmap.height())))

        crop_widget = self._image_to_widget_rect(self._crop_rect)
        shade = QColor(255, 250, 244, 165)
        painter.fillRect(QRectF(display.left(), display.top(), display.width(), crop_widget.top() - display.top()), shade)
        painter.fillRect(QRectF(display.left(), crop_widget.bottom(), display.width(), display.bottom() - crop_widget.bottom()), shade)
        painter.fillRect(QRectF(display.left(), crop_widget.top(), crop_widget.left() - display.left(), crop_widget.height()), shade)
        painter.fillRect(QRectF(crop_widget.right(), crop_widget.top(), display.right() - crop_widget.right(), crop_widget.height()), shade)

        painter.setPen(QPen(QColor(theme.ACCENT), 2))
        painter.drawRect(crop_widget)

        painter.setBrush(QColor(theme.ACCENT))
        painter.setPen(Qt.PenStyle.NoPen)
        for handle in self._handle_points().values():
            painter.drawEllipse(handle, self._HANDLE_RADIUS, self._HANDLE_RADIUS)

        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(display)
        painter.end()


class CropDialog(QDialog):
    def __init__(
        self,
        image_path: Path,
        layer_name: str,
        preset_id: str,
        canvas_size: tuple[int, int],
        initial_crop_box: CropBox | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(f"{layer_name}裁切")
        self.resize(920, 760)

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            raise ValueError(f"無法讀取圖片：{image_path.name}")

        aspect_ratio = canvas_size[0] / canvas_size[1]
        self._canvas = CropCanvas(pixmap, aspect_ratio, initial_crop_box=initial_crop_box)
        self._crop_info = QLabel("")
        self._crop_info.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        self._canvas.changed.connect(self._refresh_crop_info)

        self.setStyleSheet(
            f"""
            QDialog {{
                background: {theme.BG_PANEL};
            }}
            QLabel {{
                color: {theme.TEXT_PRIMARY};
            }}
            QPushButton {{
                background: {theme.BG_ELEVATED};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM}px;
                color: {theme.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 500;
                min-width: 80px;
                padding: 7px 14px;
            }}
            QPushButton:hover {{
                background: {theme.BG_HOVER};
                border-color: {theme.BORDER_STRONG};
                color: {theme.TEXT_PRIMARY};
            }}
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel(f"{layer_name}裁切")
        title.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")
        root.addWidget(title)

        subtitle = QLabel(
            f"{image_path.name}  ·  原圖 {pixmap.width()} × {pixmap.height()} px  ·  目標 {preset_id}"
        )
        subtitle.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px;")
        root.addWidget(subtitle)

        hint = QLabel("拖曳裁切框移動，拖曳四角調整範圍。裁切比例會鎖定目前輸出比例。")
        hint.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        root.addWidget(hint)

        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {theme.BG_ELEVATED}; border: 1px solid {theme.BORDER}; border-radius: {theme.RADIUS}px; }}"
        )
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(12, 12, 12, 12)
        frame_layout.addWidget(self._canvas, 1)
        root.addWidget(frame, 1)

        root.addWidget(self._crop_info)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._canvas.reset_crop)
        buttons.addWidget(reset_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        apply_btn = QPushButton("套用裁切")
        apply_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {theme.ACCENT};
                border: 1px solid {theme.ACCENT};
                border-radius: {theme.RADIUS_SM}px;
                color: {theme.ACCENT_ON};
                font-size: 11px;
                font-weight: 600;
                min-width: 96px;
                padding: 7px 14px;
            }}
            QPushButton:hover {{
                background: {theme.ACCENT_DIM};
                border-color: {theme.ACCENT_DIM};
                color: {theme.ACCENT_ON};
            }}
            """
        )
        apply_btn.clicked.connect(self.accept)
        buttons.addWidget(apply_btn)

        root.addLayout(buttons)
        self._refresh_crop_info()

    def _refresh_crop_info(self) -> None:
        left, top, right, bottom = self._canvas.crop_box()
        width = right - left
        height = bottom - top
        self._crop_info.setText(f"目前裁切：{left}, {top} → {right}, {bottom}  ·  {width} × {height} px")

    def crop_box(self) -> CropBox:
        return self._canvas.crop_box()
