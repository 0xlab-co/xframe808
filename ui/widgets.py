"""Reusable UI components translated from the React mockup."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ui import icons, theme


# ── Icon widget (DPR-safe, renders SVG in paintEvent) ───────────────────────
class IconLabel(QWidget):
    """Paints an SVG icon inside its actual widget rect.

    Kept the name `IconLabel` so existing imports still work, but this is no
    longer a QLabel — it's a custom-painted widget. Going through paintEvent
    means Qt handles HiDPI via the painter transform. The render rect is based
    on the widget's real bounds so the icon stays visually contained even if a
    display or layout causes the underlying size bookkeeping to drift.
    """

    def __init__(self, name: str, size: int = 13, color: str = theme.TEXT_MUTED, parent=None):
        super().__init__(parent)
        self._color = color
        self._name = name
        self._renderer = icons.make_renderer(name, color)
        self._scale = icons.icon_scale(name)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = QRectF(self.rect())
        side = min(bounds.width(), bounds.height())
        if side <= 0:
            painter.end()
            return
        content = side * self._scale
        x = bounds.x() + (bounds.width() - content) / 2.0
        y = bounds.y() + (bounds.height() - content) / 2.0
        self._renderer.render(painter, QRectF(x, y, content, content))
        painter.end()

    def set_color(self, color: str) -> None:
        self._color = color
        self._renderer = icons.make_renderer(self._name, color)
        self.update()

    def set_icon(self, name: str) -> None:
        self._name = name
        self._renderer = icons.make_renderer(name, self._color)
        self._scale = icons.icon_scale(name)
        self.update()


# ── Section header ──────────────────────────────────────────────────────────
class SectionHeader(QWidget):
    def __init__(self, icon_name: str, title_zh: str, title_en: str, action: QWidget | None = None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(7)

        icon = IconLabel(icon_name, size=11, color=theme.ACCENT)
        layout.addWidget(icon)

        zh = QLabel(title_zh)
        zh.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 12px; font-weight: 600; letter-spacing: 0.02em;"
        )
        layout.addWidget(zh)

        en = QLabel(title_en.upper())
        en.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 10px; letter-spacing: 0.06em;"
        )
        layout.addWidget(en)

        layout.addStretch(1)
        if action is not None:
            layout.addWidget(action)


# ── Preset button (custom widget for dual-size label) ───────────────────────
class PresetButton(QWidget):
    """Stacked 2-line button: large main label + tiny caption.

    Implements its own clicked/toggled signals so we can render two font sizes
    in one hit zone — QPushButton can't style two lines differently.
    """

    clicked = Signal()
    toggled = Signal(bool)

    def __init__(self, label: str, sublabel: str, parent=None):
        super().__init__(parent)
        self._checked = False
        self.setObjectName("PresetButton")
        self.setFixedHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        v = QVBoxLayout(self)
        v.setContentsMargins(4, 6, 4, 6)
        v.setSpacing(2)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)

        mono = theme.mono_family()
        self._main = QLabel(label)
        self._main.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main.setStyleSheet(
            f"font-family: '{mono}'; font-size: 13px; font-weight: 600; letter-spacing: 0.03em; background: transparent; border: none;"
        )
        self._sub = QLabel(sublabel)
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub.setStyleSheet(
            f"font-family: '{mono}'; font-size: 9px; letter-spacing: 0.04em; background: transparent; border: none;"
        )
        v.addWidget(self._main)
        v.addWidget(self._sub)

        self._refresh_style()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        value = bool(value)
        if value == self._checked:
            return
        self._checked = value
        self._refresh_style()
        self.toggled.emit(value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.setChecked(True)
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hovering = True
        self._refresh_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovering = False
        self._refresh_style()
        super().leaveEvent(event)

    def _refresh_style(self) -> None:
        hovering = getattr(self, "_hovering", False)
        if self._checked:
            bg = theme.ACCENT_GLOW
            border = theme.ACCENT_BORDER
            color = theme.ACCENT
            sub_color = theme.ACCENT
        elif hovering:
            bg = theme.BG_HOVER
            border = theme.BORDER_STRONG
            color = theme.TEXT_PRIMARY
            sub_color = theme.TEXT_SECONDARY
        else:
            bg = theme.BG_ELEVATED
            border = theme.BORDER
            color = theme.TEXT_SECONDARY
            sub_color = theme.TEXT_MUTED
        self.setStyleSheet(
            f"#PresetButton {{ background: {bg}; border: 1px solid {border}; border-radius: {theme.RADIUS}px; }}"
        )
        mono = theme.mono_family()
        self._main.setStyleSheet(
            f"color: {color}; font-family: '{mono}'; font-size: 13px; font-weight: 600; letter-spacing: 0.03em; background: transparent; border: none;"
        )
        self._sub.setStyleSheet(
            f"color: {sub_color}; font-family: '{mono}'; font-size: 9px; letter-spacing: 0.04em; background: transparent; border: none;"
        )


# ── Path row ────────────────────────────────────────────────────────────────
class PathRow(QWidget):
    browse_requested = Signal()
    crop_requested = Signal()
    clear_requested = Signal()

    def __init__(
        self,
        icon_name: str,
        label_zh: str,
        label_en: str,
        placeholder: str = "尚未選擇…",
        *,
        show_crop: bool = False,
        show_clear: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._show_crop = show_crop
        self._show_clear = show_clear
        self._cropped = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(5)

        # Row 1: label line
        label_row = QHBoxLayout()
        label_row.setSpacing(6)
        label_row.setContentsMargins(0, 0, 0, 0)

        icon = IconLabel(icon_name, size=10, color=theme.TEXT_MUTED)
        label_row.addWidget(icon)

        zh = QLabel(label_zh)
        zh.setStyleSheet(
            f"color: {theme.TEXT_SECONDARY}; font-size: 11px; font-weight: 500; letter-spacing: 0.02em;"
        )
        label_row.addWidget(zh)

        en = QLabel(label_en.upper())
        en.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px; letter-spacing: 0.05em;")
        label_row.addWidget(en)

        label_row.addStretch(1)
        outer.addLayout(label_row)

        # Row 2: value display + browse button
        value_row = QHBoxLayout()
        value_row.setSpacing(6)
        value_row.setContentsMargins(0, 0, 0, 0)

        mono = theme.mono_family()
        self._value = QLineEdit()
        self._value.setReadOnly(True)
        self._value.setPlaceholderText(placeholder)
        self._value.setFixedHeight(30)
        self._value.setStyleSheet(
            f"""
            QLineEdit {{
                background: {theme.BG_BASE};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM}px;
                padding: 0 10px;
                font-family: "{mono}";
                font-size: 11px;
                color: {theme.TEXT_PRIMARY};
            }}
            QLineEdit:disabled {{
                color: {theme.TEXT_MUTED};
            }}
            """
        )
        value_row.addWidget(self._value, 1)

        self._browse = QPushButton("選擇…")
        self._browse.setFixedSize(60, 30)
        self._browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse.setStyleSheet(self._button_style())
        self._browse.clicked.connect(self.browse_requested.emit)
        value_row.addWidget(self._browse)

        if self._show_crop:
            self._crop = QPushButton("裁切")
            self._crop.setFixedSize(48, 30)
            self._crop.setCursor(Qt.CursorShape.PointingHandCursor)
            self._crop.clicked.connect(self.crop_requested.emit)
            value_row.addWidget(self._crop)
        else:
            self._crop = None

        if self._show_clear:
            self._clear = QPushButton("移除")
            self._clear.setFixedSize(48, 30)
            self._clear.setCursor(Qt.CursorShape.PointingHandCursor)
            self._clear.clicked.connect(self.clear_requested.emit)
            value_row.addWidget(self._clear)
        else:
            self._clear = None

        outer.addLayout(value_row)
        self._refresh_action_buttons()

    def _button_style(self, *, emphasized: bool = False) -> str:
        if emphasized:
            background = theme.ACCENT_GLOW
            border = theme.ACCENT_BORDER
            color = theme.ACCENT
            hover = theme.BG_HOVER
        else:
            background = theme.BG_ELEVATED
            border = theme.BORDER
            color = theme.TEXT_SECONDARY
            hover = theme.BG_HOVER
        return f"""
            QPushButton {{
                background: {background};
                border: 1px solid {border};
                border-radius: {theme.RADIUS_SM}px;
                color: {color};
                font-size: 11px;
                font-weight: 500;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background: {hover};
                border-color: {theme.BORDER_STRONG};
                color: {theme.TEXT_PRIMARY};
            }}
            QPushButton:disabled {{
                color: {theme.TEXT_MUTED};
                border-color: {theme.BORDER};
                background: {theme.BG_ELEVATED};
            }}
        """

    def _refresh_action_buttons(self) -> None:
        has_value = bool(self._value.text())
        if self._crop is not None:
            self._crop.setEnabled(has_value)
            self._crop.setText("已裁切" if self._cropped else "裁切")
            self._crop.setStyleSheet(self._button_style(emphasized=self._cropped))
        if self._clear is not None:
            self._clear.setEnabled(has_value)
            self._clear.setStyleSheet(self._button_style())

    def text(self) -> str:
        return self._value.text()

    def set_text(self, value: str) -> None:
        self._value.setText(value)
        self._value.setToolTip(value)
        self._refresh_action_buttons()

    def clear(self) -> None:
        self._value.clear()
        self._value.setToolTip("")
        self._refresh_action_buttons()

    def set_cropped(self, cropped: bool) -> None:
        self._cropped = cropped
        self._refresh_action_buttons()


# ── Slider row ──────────────────────────────────────────────────────────────
class SliderRow(QWidget):
    value_changed = Signal(int)

    def __init__(
        self,
        label_zh: str,
        label_en: str,
        minimum: int,
        maximum: int,
        default: int,
        fmt: Callable[[int], str],
        parent=None,
    ):
        super().__init__(parent)
        self._fmt = fmt

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        # Label block (zh + en stacked)
        label_col = QVBoxLayout()
        label_col.setContentsMargins(0, 0, 0, 0)
        label_col.setSpacing(0)
        zh = QLabel(label_zh)
        zh.setStyleSheet(
            f"color: {theme.TEXT_SECONDARY}; font-size: 11px; font-weight: 500;"
        )
        en = QLabel(label_en.upper())
        en.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 10px; letter-spacing: 0.05em;"
        )
        label_col.addWidget(zh)
        label_col.addWidget(en)

        label_wrap = QWidget()
        label_wrap.setFixedWidth(90)
        label_wrap.setLayout(label_col)
        row.addWidget(label_wrap)

        # Slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setMinimum(minimum)
        self._slider.setMaximum(maximum)
        self._slider.setValue(default)
        self._slider.setStyleSheet(
            f"""
            QSlider::groove:horizontal {{
                height: 2px;
                background: {theme.BG_ACTIVE};
                border-radius: 1px;
            }}
            QSlider::sub-page:horizontal {{
                background: {theme.ACCENT};
                border-radius: 1px;
            }}
            QSlider::add-page:horizontal {{
                background: {theme.BG_ACTIVE};
                border-radius: 1px;
            }}
            QSlider::handle:horizontal {{
                background: {theme.ACCENT};
                width: 12px;
                height: 12px;
                margin: -6px 0;
                border-radius: 7px;
                border: 2px solid {theme.BG_PANEL};
            }}
            QSlider::handle:horizontal:hover {{
                background: {theme.ACCENT_DIM};
            }}
            """
        )
        row.addWidget(self._slider, 1)

        # Value label
        mono = theme.mono_family()
        self._value_label = QLabel(fmt(default))
        self._value_label.setFixedWidth(56)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._value_label.setStyleSheet(
            f"color: {theme.ACCENT}; font-family: '{mono}'; font-size: 11px; font-weight: 500;"
        )
        row.addWidget(self._value_label)

        self._slider.valueChanged.connect(self._on_changed)

    def _on_changed(self, value: int) -> None:
        self._value_label.setText(self._fmt(value))
        self.value_changed.emit(value)

    def value(self) -> int:
        return self._slider.value()

    def set_value(self, value: int) -> None:
        self._slider.setValue(value)


# ── Primary / danger action button ──────────────────────────────────────────
class ActionButton(QFrame):
    """Bottom sticky action with custom icon layout so scaling stays exact."""

    clicked = Signal()

    MODE_IDLE = "idle"
    MODE_RUNNING = "running"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ActionButton")
        self.setFixedHeight(38)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._hovering = False

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(7)
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon = IconLabel("play", size=10, color=theme.TEXT_MUTED)
        self._label = QLabel("")
        self._label.setStyleSheet("background: transparent; border: none;")
        row.addWidget(self._icon)
        row.addWidget(self._label)

        self._mode = self.MODE_IDLE
        self.set_mode(self.MODE_IDLE, enabled=False)

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.isEnabled()
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._hovering = True
        self._refresh_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovering = False
        self._refresh_style()
        super().leaveEvent(event)

    def _refresh_style(self) -> None:
        if not self.isEnabled():
            background = theme.BG_ELEVATED
            border = theme.BORDER
            label_color = theme.TEXT_MUTED
        elif self._mode == self.MODE_RUNNING:
            background = "rgba(184, 95, 77, 0.18)" if self._hovering else theme.DANGER_GLOW
            border = theme.DANGER_BORDER
            label_color = theme.DANGER
        else:
            background = theme.ACCENT_DIM if self._hovering else theme.ACCENT
            border = theme.ACCENT if self._hovering else theme.ACCENT
            label_color = theme.ACCENT_ON

        self.setStyleSheet(
            f"#ActionButton {{ background: {background}; border: 1px solid {border}; border-radius: {theme.RADIUS}px; }}"
        )
        self._label.setStyleSheet(
            f"color: {label_color}; font-size: 13px; font-weight: 600; letter-spacing: 0.01em; background: transparent; border: none;"
        )
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if self.isEnabled() else Qt.CursorShape.ArrowCursor
        )

    def set_mode(self, mode: str, *, enabled: bool) -> None:
        self._mode = mode
        if mode == self.MODE_RUNNING:
            text = "取消  Cancel"
            icon_name = "stop"
            icon_color = theme.DANGER
            effective_enabled = True
        elif enabled:
            text = "開始套框  Batch"
            icon_name = "play"
            icon_color = theme.ACCENT_ON
            effective_enabled = True
        else:
            text = "開始套框  Batch"
            icon_name = "play"
            icon_color = theme.TEXT_MUTED
            effective_enabled = False

        super().setEnabled(effective_enabled)
        self._label.setText(text)
        self._icon.set_icon(icon_name)
        self._icon.set_color(icon_color)
        self._refresh_style()
