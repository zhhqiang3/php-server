"""离屏截图：把各页面渲染成 PNG，方便肉眼检查 UI。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

from gui.appearance import apply_appearance  # noqa: E402

OUT = Path(os.environ.get("SHOT_DIR", ROOT / "shots"))
OUT.mkdir(parents=True, exist_ok=True)


def shot(widget, name: str) -> None:
    widget.resize(1080, 720)
    widget.show()
    app.processEvents()
    path = OUT / f"{name}.png"
    widget.grab().save(str(path))
    print(f"saved {path}")


def main() -> None:
    theme = os.environ.get("SHOT_THEME", "深色")
    apply_appearance(app, theme=theme, font_size=10)

    import core.nginx_manager as nm

    nm.NginxManager.running = lambda self: False
    nm.NginxManager.version = lambda self: "1.31.8"
    nm.NginxManager.installed = lambda self: True

    from gui.main import MainWindow

    win = MainWindow()
    win.resize(1080, 720)
    win.show()
    app.processEvents()

    tabs = win.tabs
    order = ["首页", "站点", "PHP", "php.ini", "Nginx", "Hosts", "日志"]
    for i in range(tabs.count()):
        tabs.setCurrentIndex(i)
        app.processEvents()
        name = order[i] if i < len(order) else f"tab{i}"
        shot(win, f"{theme}-{i}-{name}")

    # php.ini 页（隐藏页签，也要单独截）
    win.show_ini("8.4.27")
    app.processEvents()
    shot(win, f"{theme}-ini-page")

    # php.ini 的扩展页
    from PyQt6.QtWidgets import QTabWidget

    for tabs in win.ini_page.findChildren(QTabWidget):
        if tabs.count() == 3:
            tabs.setCurrentIndex(1)
            break
    app.processEvents()
    shot(win, f"{theme}-ini-ext")

    for tabs in win.ini_page.findChildren(QTabWidget):
        if tabs.count() == 3:
            tabs.setCurrentIndex(2)
            break
    app.processEvents()
    shot(win, f"{theme}-ini-raw")


if __name__ == "__main__":
    main()
