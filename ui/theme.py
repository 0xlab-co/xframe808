"""Warm cream light theme tokens and global stylesheet for xFRAME808.

Translated from the React/HTML mockup at docs/ui_redesign. Color values are the
hex approximations of the original `oklch(...)` tokens.
"""
from __future__ import annotations

from PySide6.QtGui import QFontDatabase

# ── Color tokens ────────────────────────────────────────────────────────────
# Claude-like light palette: cream surfaces, warm brown text, terracotta
# accent, and soft beige preview matte.
BG_BASE = "#f6efe6"
BG_PANEL = "#fbf7f0"
BG_ELEVATED = "#fffaf4"
BG_HOVER = "#f1e7db"
BG_ACTIVE = "#e8dccd"

BORDER = "#e3d6c7"
BORDER_STRONG = "#d4c2b0"

TEXT_PRIMARY = "#4a392c"
TEXT_SECONDARY = "#6c5848"
TEXT_MUTED = "#9b8776"

ACCENT = "#b86543"
ACCENT_DIM = "#a55637"
ACCENT_GLOW = "rgba(184, 101, 67, 0.12)"
ACCENT_BORDER = "rgba(184, 101, 67, 0.30)"
ACCENT_ON = "#fff8f3"

SUCCESS = "#748b5c"
SUCCESS_GLOW = "rgba(116, 139, 92, 0.12)"
SUCCESS_BORDER = "rgba(116, 139, 92, 0.30)"

DANGER = "#b85f4d"
DANGER_GLOW = "rgba(184, 95, 77, 0.12)"
DANGER_BORDER = "rgba(184, 95, 77, 0.30)"

PREVIEW_MATTE = "#f2e8dc"
PREVIEW_CHECKER = "#eadccc"

# ── Radius tokens ───────────────────────────────────────────────────────────
RADIUS_SM = 5
RADIUS = 8
RADIUS_LG = 12


# ── Font resolution ─────────────────────────────────────────────────────────
def _pick_family(candidates: tuple[str, ...], fallback: str) -> str:
    families = set(QFontDatabase.families())
    for name in candidates:
        if name in families:
            return name
    return fallback


def resolve_fonts() -> tuple[str, str]:
    """Return (display_family, mono_family) matching what's available on the host."""
    display = _pick_family(
        ("Space Grotesk", "SF Pro Display", "SF Pro Text", "Helvetica Neue", "Segoe UI"),
        "sans-serif",
    )
    mono = _pick_family(
        ("JetBrains Mono", "SF Mono", "Menlo", "Cascadia Mono", "Consolas"),
        "monospace",
    )
    return display, mono


def build_global_stylesheet() -> str:
    """QSS applied at QApplication level. Covers base chrome, scrollbars, dialogs."""
    display, mono = resolve_fonts()
    return f"""
        * {{
            font-family: "{display}";
            font-size: 12px;
        }}
        QWidget {{
            background-color: {BG_BASE};
            color: {TEXT_PRIMARY};
        }}
        QMainWindow, QDialog {{
            background-color: {BG_BASE};
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 6px;
            margin: 2px 0;
        }}
        QScrollBar::handle:vertical {{
            background: {BORDER_STRONG};
            border-radius: 2px;
            min-height: 24px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
        QScrollBar:horizontal {{
            background: {BG_ACTIVE};
            height: 10px;
            margin: 0;
            border-top: 1px solid {BORDER};
        }}
        QScrollBar::handle:horizontal {{
            background: {BORDER_STRONG};
            border-radius: 4px;
            min-width: 40px;
            margin: 2px 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {TEXT_MUTED};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
            background: transparent;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}
        QMessageBox {{
            background-color: {BG_PANEL};
        }}
        QMessageBox QLabel {{
            color: {TEXT_PRIMARY};
            font-size: 12px;
        }}
        QMessageBox QPushButton {{
            background: {BG_ELEVATED};
            border: 1px solid {BORDER};
            border-radius: {RADIUS_SM}px;
            color: {TEXT_PRIMARY};
            padding: 6px 16px;
            min-width: 72px;
        }}
        QMessageBox QPushButton:hover {{
            background: {BG_HOVER};
            border-color: {BORDER_STRONG};
        }}
        QToolTip {{
            background-color: {BG_ELEVATED};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_STRONG};
            padding: 4px 8px;
        }}
    """


# ── Mono font helper ────────────────────────────────────────────────────────
def mono_family() -> str:
    return resolve_fonts()[1]
