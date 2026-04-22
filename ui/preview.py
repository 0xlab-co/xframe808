"""Preview pane: header bar + checker-background canvas that renders the
currently computed composite pixmap with aspect-ratio fit.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPixmap, QBrush, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.widgets import IconLabel


class _Canvas(QWidget):
    """Paints the preview canvas: checker background, aspect-fit pixmap or
    centered status text. Aspect ratio matches the selected preset canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._aspect_ratio: tuple[int, int] = (1, 1)
        self._status: str | None = "選擇輸出比例與圖層後\n自動顯示合成預覽"
        self._status_error: bool = False
        self.setMinimumSize(200, 200)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def set_aspect_ratio(self, width: int, height: int) -> None:
        self._aspect_ratio = (max(1, width), max(1, height))
        self.update()

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        self._status = None
        self._status_error = False
        self.update()

    def set_status(self, message: str, *, error: bool = False) -> None:
        self._pixmap = None
        self._status = message
        self._status_error = error
        self.update()

    def _fit_rect(self) -> QRectF:
        aw, ah = self._aspect_ratio
        padding = 24
        avail_w = max(1, self.width() - padding * 2)
        avail_h = max(1, self.height() - padding * 2)
        target_ratio = aw / ah
        avail_ratio = avail_w / avail_h
        if avail_ratio > target_ratio:
            h = avail_h
            w = int(h * target_ratio)
        else:
            w = avail_w
            h = int(w / target_ratio)
        x = (self.width() - w) / 2
        y = (self.height() - h) / 2
        return QRectF(x, y, w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Canvas background (entire widget)
        painter.fillRect(self.rect(), QColor(theme.BG_BASE))

        rect = self._fit_rect()
        # Checker pattern inside the fit rect
        painter.save()
        painter.setClipRect(rect)
        painter.fillRect(rect, QColor(theme.PREVIEW_MATTE))
        checker = QColor(theme.PREVIEW_CHECKER)
        size = 8
        x0 = int(rect.x())
        y0 = int(rect.y())
        x1 = int(rect.right()) + size
        y1 = int(rect.bottom()) + size
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(checker))
        for y in range(y0, y1, size):
            for x in range(x0, x1, size):
                if ((x // size) + (y // size)) % 2 == 0:
                    painter.drawRect(x, y, size, size)
        painter.restore()

        # Border + shadow-ish outline
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

        # Foreground: pixmap or status text
        if self._pixmap is not None and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                rect.size().toSize(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            sx = rect.x() + (rect.width() - scaled.width()) / 2
            sy = rect.y() + (rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(sx), int(sy), scaled)
        elif self._status:
            color = QColor(theme.DANGER) if self._status_error else QColor(theme.TEXT_MUTED)
            painter.setPen(color)
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._status)

        painter.end()


class PreviewPane(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"PreviewPane {{ background: {theme.BG_BASE}; border-left: 1px solid {theme.BORDER}; }}"
        )
        self.setObjectName("PreviewPane")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(38)
        header.setStyleSheet(f"background: {theme.BG_BASE}; border-bottom: 1px solid {theme.BORDER};")
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(16, 0, 16, 0)
        header_row.setSpacing(10)

        header_row.addWidget(IconLabel("output", size=10, color=theme.ACCENT))
        zh = QLabel("預覽")
        zh.setStyleSheet(
            f"color: {theme.TEXT_SECONDARY}; font-size: 11px; font-weight: 500; letter-spacing: 0.03em;"
        )
        header_row.addWidget(zh)
        en = QLabel("PREVIEW")
        en.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px; letter-spacing: 0.06em;")
        header_row.addWidget(en)

        header_row.addStretch(1)

        mono = theme.mono_family()
        self._dim_label = QLabel("")
        self._dim_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-family: '{mono}'; font-size: 10px;"
        )
        header_row.addWidget(self._dim_label)

        root.addWidget(header)

        self._canvas = _Canvas()
        root.addWidget(self._canvas, 1)

    def set_preset(self, preset_id: str, canvas_size: tuple[int, int]) -> None:
        w, h = canvas_size
        self._canvas.set_aspect_ratio(w, h)
        self._dim_label.setText(f"{w} × {h} px  ·  {preset_id}")

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        self._canvas.set_pixmap(pixmap)

    def set_status(self, message: str, *, error: bool = False) -> None:
        self._canvas.set_status(message, error=error)
