"""Inline SVG icons, translated from the feather-icon set used in the HTML
mockup. Two render paths:

- `make_pixmap(...)` for QIcon / QPushButton icons, where a raster is needed.
- `IconWidget` (see widgets.py) for inline decoration, which paints the SVG
  directly in its paintEvent. The widget path is DPR-safe — Qt handles HiDPI
  via the painter transform, so we never fight pixel ratios manually.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Raw inner markup (viewBox 0 0 24 24). We wrap with the right stroke color
# per request so tint can follow theme state.
_ICON_PATHS: dict[str, str] = {
    "image": (
        '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>'
        '<circle cx="8.5" cy="8.5" r="1.5"/>'
        '<polyline points="21 15 16 10 5 21"/>'
    ),
    "folder": (
        '<path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>'
    ),
    "refresh": (
        '<polyline points="1 4 1 10 7 10"/>'
        '<path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>'
    ),
    "play": '<polygon points="5 3 19 12 5 21 5 3"/>',
    "stop": '<rect x="3" y="3" width="18" height="18" rx="1"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "alert": (
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="12" y1="8" x2="12" y2="12"/>'
        '<line x1="12" y1="16" x2="12.01" y2="16"/>'
    ),
    "x": (
        '<line x1="18" y1="6" x2="6" y2="18"/>'
        '<line x1="6" y1="6" x2="18" y2="18"/>'
    ),
    "layers": (
        '<polygon points="12 2 2 7 12 12 22 7 12 2"/>'
        '<polyline points="2 17 12 22 22 17"/>'
        '<polyline points="2 12 12 17 22 12"/>'
    ),
    "sliders": (
        '<line x1="4" y1="21" x2="4" y2="14"/>'
        '<line x1="4" y1="10" x2="4" y2="3"/>'
        '<line x1="12" y1="21" x2="12" y2="12"/>'
        '<line x1="12" y1="8" x2="12" y2="3"/>'
        '<line x1="20" y1="21" x2="20" y2="16"/>'
        '<line x1="20" y1="12" x2="20" y2="3"/>'
        '<line x1="1" y1="14" x2="7" y2="14"/>'
        '<line x1="9" y1="8" x2="15" y2="8"/>'
        '<line x1="17" y1="16" x2="23" y2="16"/>'
    ),
    "output": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
}

# Per-icon visual-weight correction. Feather icons share a 24×24 viewBox, but
# their content bounding boxes differ — "layers" and "folder" fill the full
# square, while "zap" is a thin diagonal shape. Without correction, dense
# icons look ~30% larger than thin ones at the same pixel size. These factors
# scale each icon's render rect down so the perceived size is uniform.
_ICON_SCALE: dict[str, float] = {
    "image": 0.90,
    "folder": 0.88,
    "refresh": 0.92,
    "play": 0.90,
    "stop": 0.82,
    "check": 0.92,
    "alert": 0.88,
    "x": 0.92,
    "layers": 0.86,
    "sliders": 0.88,
    "output": 0.96,
    "zap": 1.00,
}


def _svg_document(name: str, color: str) -> bytes:
    inner = _ICON_PATHS[name]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round">'
        f"{inner}</svg>"
    )
    return svg.encode("utf-8")


def make_renderer(name: str, color: str) -> QSvgRenderer:
    """Build a QSvgRenderer for direct paintEvent use."""
    return QSvgRenderer(QByteArray(_svg_document(name, color)))


def icon_scale(name: str) -> float:
    return _ICON_SCALE.get(name, 1.0)


def make_pixmap(name: str, size: int, color: str, device_pixel_ratio: float = 2.0) -> QPixmap:
    """Render an icon to a QPixmap at the requested logical size.

    Uses a 2× device pixel ratio by default so the icon stays crisp on HiDPI.
    """
    if name not in _ICON_PATHS:
        raise KeyError(f"unknown icon: {name}")

    physical = int(size * device_pixel_ratio)
    px = QPixmap(QSize(physical, physical))
    px.setDevicePixelRatio(device_pixel_ratio)
    px.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(QByteArray(_svg_document(name, color)))
    # Scale content rect per-icon so visual weight stays uniform across icons.
    scale = _ICON_SCALE.get(name, 1.0)
    content = physical * scale
    margin = (physical - content) / 2.0

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(margin, margin, content, content))
    painter.end()
    return px
