"""Horizontal thumbnail strip for product selection.

Lives under the preview canvas. Clicking a thumbnail picks it as the current
product (preview updates + its per-product transform panel expands).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QScrollBar,
    QVBoxLayout,
    QWidget,
)

from core.video import is_video_file, read_first_frame
from ui import icons, theme

THUMB_SIZE = 72
STRIP_HEIGHT = 128
ITEM_PADDING = 6


def _pil_to_qpixmap(pil_image) -> QPixmap:
    rgba = pil_image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, rgba.width, rgba.height, 4 * rgba.width, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


def _load_thumb_pixmap(path: Path) -> QPixmap | None:
    try:
        if is_video_file(path):
            frame = read_first_frame(path)
            return _pil_to_qpixmap(frame)
        pix = QPixmap(str(path))
        if pix.isNull():
            return None
        return pix
    except Exception:
        return None


class _ThumbnailScrollArea(QScrollArea):
    """Horizontal strip with Chrome-like wheel behavior.

    Mouse wheels and most trackpads emit vertical deltas by default. In a
    horizontal thumbnail rail that feels broken, so translate vertical wheel
    motion into horizontal scrolling unless the user is already scrolling on
    the X axis.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("ThumbnailScrollArea")
        self.setStyleSheet(
            f"""
            QScrollArea#ThumbnailScrollArea {{
                background: {theme.BG_PANEL};
                border: none;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                border: none;
                height: 12px;
                margin: 2px 12px 8px 12px;
            }}
            QScrollBar::handle:horizontal {{
                background: rgba(108, 88, 72, 0.34);
                border-radius: 5px;
                min-width: 52px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: rgba(108, 88, 72, 0.52);
            }}
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: rgba(155, 135, 118, 0.14);
                border-radius: 5px;
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0;
                background: transparent;
            }}
            """
        )
        bar = self.horizontalScrollBar()
        bar.setSingleStep(48)
        bar.setPageStep(240)

    def wheelEvent(self, event):
        delta = event.angleDelta()
        if abs(delta.x()) > abs(delta.y()):
            super().wheelEvent(event)
            return

        bar: QScrollBar = self.horizontalScrollBar()
        if not bar.isVisible():
            super().wheelEvent(event)
            return

        pixel_delta = event.pixelDelta().y()
        if pixel_delta:
            bar.setValue(bar.value() - pixel_delta)
            event.accept()
            return

        angle_delta = delta.y()
        if angle_delta:
            step_count = angle_delta / 120.0
            travel = int(round(step_count * max(36, bar.singleStep()) * 2.5))
            bar.setValue(bar.value() - travel)
            event.accept()
            return

        super().wheelEvent(event)


class _Thumb(QFrame):
    clicked = Signal(str)  # abs path

    def __init__(self, path: Path, pixmap: QPixmap | None, parent=None):
        super().__init__(parent)
        self._path = path
        self._pixmap = pixmap
        self._is_video = is_video_file(path)
        self._selected = False
        self._hovering = False
        self.setFixedSize(THUMB_SIZE + ITEM_PADDING * 2, THUMB_SIZE + ITEM_PADDING * 2 + 14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(path.name)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def path(self) -> Path:
        return self._path

    def set_selected(self, selected: bool) -> None:
        if selected == self._selected:
            return
        self._selected = selected
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.clicked.emit(str(self._path))
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hovering = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovering = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Thumbnail frame
        frame_rect = QRectF(ITEM_PADDING, ITEM_PADDING, THUMB_SIZE, THUMB_SIZE)
        bg_color = QColor(theme.BG_ELEVATED)
        painter.fillRect(frame_rect, bg_color)

        # Pixmap contain-fit
        if self._pixmap is not None and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                int(frame_rect.width()),
                int(frame_rect.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            px = frame_rect.x() + (frame_rect.width() - scaled.width()) / 2
            py = frame_rect.y() + (frame_rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(px), int(py), scaled)
        else:
            painter.setPen(QColor(theme.TEXT_MUTED))
            painter.drawText(frame_rect, Qt.AlignmentFlag.AlignCenter, "?")

        # Border
        if self._selected:
            pen = QPen(QColor(theme.ACCENT), 2)
        elif self._hovering:
            pen = QPen(QColor(theme.BORDER_STRONG), 1)
        else:
            pen = QPen(QColor(theme.BORDER), 1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(frame_rect)

        # Video badge
        if self._is_video:
            badge_size = 16
            badge_rect = QRectF(
                frame_rect.right() - badge_size - 3,
                frame_rect.bottom() - badge_size - 3,
                badge_size,
                badge_size,
            )
            painter.setBrush(QColor(0, 0, 0, 170))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect, 3, 3)
            renderer = icons.make_renderer("video", "#ffffff")
            inner = badge_size * 0.72
            offset = (badge_size - inner) / 2
            renderer.render(
                painter,
                QRectF(badge_rect.x() + offset, badge_rect.y() + offset, inner, inner),
            )

        # Filename (truncated by Qt eliding via drawText)
        text_rect = QRectF(
            0,
            frame_rect.bottom() + 2,
            self.width(),
            self.height() - frame_rect.bottom() - 2,
        )
        painter.setPen(QColor(theme.ACCENT) if self._selected else QColor(theme.TEXT_MUTED))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        fm = painter.fontMetrics()
        elided = fm.elidedText(self._path.name, Qt.TextElideMode.ElideMiddle, int(text_rect.width()) - 4)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, elided)

        painter.end()


class ThumbnailStrip(QFrame):
    thumbnail_clicked = Signal(str)  # abs path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ThumbnailStrip")
        self.setStyleSheet(
            f"#ThumbnailStrip {{ background: {theme.BG_PANEL}; border-top: 1px solid {theme.BORDER}; }}"
        )
        self.setFixedHeight(STRIP_HEIGHT)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = _ThumbnailScrollArea()
        outer.addWidget(self._scroll)

        self._content = QWidget()
        self._content.setStyleSheet(f"background: {theme.BG_PANEL};")
        self._row = QHBoxLayout(self._content)
        self._row.setContentsMargins(12, 8, 12, 4)
        self._row.setSpacing(6)
        self._row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._placeholder = QLabel("選好商品資料夾後，這裡會列出縮圖  ·  Pick a product folder")
        self._placeholder.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 11px; padding: 0 12px;"
        )
        self._row.addWidget(self._placeholder)

        self._scroll.setWidget(self._content)

        self._thumbs: dict[str, _Thumb] = {}
        self._selected_path: str | None = None

    def clear(self) -> None:
        for thumb in self._thumbs.values():
            thumb.setParent(None)
            thumb.deleteLater()
        self._thumbs.clear()
        self._selected_path = None
        self._placeholder.setVisible(True)

    def set_products(self, paths: list[Path]) -> None:
        self.clear()
        if not paths:
            return
        self._placeholder.setVisible(False)
        # Insert before the stretch-less placeholder to keep left alignment.
        # Remove placeholder from layout while we populate; keep reference.
        self._row.removeWidget(self._placeholder)
        self._placeholder.setParent(self._content)
        self._placeholder.setVisible(False)
        for path in paths:
            pix = _load_thumb_pixmap(path)
            thumb = _Thumb(path, pix, parent=self._content)
            thumb.clicked.connect(self.thumbnail_clicked.emit)
            self._row.addWidget(thumb)
            self._thumbs[str(path)] = thumb

    def set_selected(self, path_str: str | None) -> None:
        if self._selected_path == path_str:
            return
        if self._selected_path and self._selected_path in self._thumbs:
            self._thumbs[self._selected_path].set_selected(False)
        self._selected_path = path_str
        if path_str and path_str in self._thumbs:
            self._thumbs[path_str].set_selected(True)
            self._scroll.ensureWidgetVisible(self._thumbs[path_str])
