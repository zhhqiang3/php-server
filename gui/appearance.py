"""外观设置：主题（明/暗/跟随系统）与字体大小，持久化到 config.yaml。"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from core.paths import load_config, save_config

THEMES = ("跟随系统", "深色", "浅色")
FONT_SIZES = (9, 10, 11, 12, 13, 14, 16, 18)


def current_theme() -> str:
    return str(load_config().get("ui", {}).get("theme", "跟随系统"))


def current_font_size() -> int:
    return int(load_config().get("ui", {}).get("font_size", 10))


def save_appearance(theme: str, font_size: int) -> None:
    cfg = load_config()
    cfg.setdefault("ui", {})["theme"] = theme
    cfg["ui"]["font_size"] = int(font_size)
    save_config(cfg)


def is_dark(app: QApplication) -> bool:
    """当前用的是不是深色底。"""
    if current_theme() == "深色":
        return True
    if current_theme() == "浅色":
        return False
    from PyQt6.QtCore import Qt

    return app.styleHints().colorScheme() == Qt.ColorScheme.Dark


def apply_appearance(app: QApplication, theme: str = None, font_size: int = None) -> None:
    """设置全局字体与调色板。参数缺省时从配置读取。"""
    cfg = load_config().get("ui", {})
    theme = theme or cfg.get("theme", "跟随系统")
    font_size = int(font_size or cfg.get("font_size", 10))

    font = app.font()
    font.setPointSize(font_size)
    app.setFont(font)

    app.setStyle("Fusion")
    if theme == "浅色":
        palette = _light_palette()
        dark = False
    elif theme == "深色":
        palette = _dark_palette()
        dark = True
    else:
        # 跟随系统：由 Qt 判断深浅
        from PyQt6.QtCore import Qt

        dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        palette = _dark_palette() if dark else _light_palette()
    app.setPalette(palette)

    from gui.ui import build_stylesheet, header_style

    app.setStyleSheet(build_stylesheet(dark) + header_style(dark))


def _dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(32, 32, 32))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Base, QColor(24, 24, 24))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 40))
    palette.setColor(QPalette.ColorRole.Text, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Button, QColor(48, 48, 48))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(48, 48, 48))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(45, 110, 180))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(130, 130, 130))
    return palette


def _light_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.Text, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.Button, QColor(225, 225, 225))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(45, 110, 180))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(150, 150, 150))
    return palette
