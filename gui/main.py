"""PHP / Nginx 管理器主窗口。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QStatusBar,
    QTabWidget,
    QWidget,
)

from core.php_manager import PHPManager
from gui.appearance import (
    FONT_SIZES,
    THEMES,
    apply_appearance,
    current_font_size,
    current_theme,
    save_appearance,
)
from gui.hosts_page import HostsPage
from gui.ini_page import IniPage
from gui.log_page import LogPage
from gui.nginx_page import NginxPage
from gui.php_page import PhpPage
from gui.site_page import SitePage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PHP / Nginx 管理器")
        self.resize(1080, 720)

        self.php_page = PhpPage()
        self.site_page = SitePage(self.php_page.mgr)
        self.ini_page = IniPage(self.php_page.mgr)
        self.nginx_page = NginxPage()
        self.hosts_page = HostsPage()
        self.log_page = LogPage()

        tabs = QTabWidget()
        tabs.addTab(self.php_page, "PHP")
        tabs.addTab(self.site_page, "站点")
        tabs.addTab(self.ini_page, "php.ini")
        tabs.addTab(self.nginx_page, "Nginx")
        tabs.addTab(self.hosts_page, "Hosts")
        tabs.addTab(self.log_page, "日志")
        tabs.currentChanged.connect(self._on_tab)
        self.setCentralWidget(tabs)

        self._build_menus()

        self.setStatusBar(QStatusBar())
        self.php_page.changed.connect(self._sync)
        self._sync()

    def _build_menus(self) -> None:
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close)
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(quit_action)

        # 设置菜单：主题单选 + 字体大小单选
        settings_menu = self.menuBar().addMenu("设置")

        theme_menu = QMenu("主题", self)
        self._theme_actions = []
        current = current_theme()
        for name in THEMES:
            action = QAction(name, self, checkable=True)
            action.setChecked(name == current)
            action.triggered.connect(lambda checked, n=name: self._set_theme(n))
            theme_menu.addAction(action)
            self._theme_actions.append(action)
        settings_menu.addMenu(theme_menu)

        font_menu = QMenu("字体大小", self)
        self._font_actions = []
        size_now = current_font_size()
        for size in FONT_SIZES:
            action = QAction(f"{size} pt", self, checkable=True)
            action.setChecked(size == size_now)
            action.triggered.connect(lambda checked, s=size: self._set_font_size(s))
            font_menu.addAction(action)
            self._font_actions.append(action)
        settings_menu.addMenu(font_menu)

    def _set_theme(self, name: str) -> None:
        save_appearance(name, current_font_size())
        for action in self._theme_actions:
            action.setChecked(action.text() == name)
        apply_appearance(QApplication.instance())

    def _set_font_size(self, size: int) -> None:
        save_appearance(current_theme(), size)
        for action in self._font_actions:
            action.setChecked(action.text() == f"{size} pt")
        apply_appearance(QApplication.instance())

    def _on_tab(self, index: int) -> None:
        if index == 0:
            self.php_page.refresh()
        elif index == 1:
            self.site_page.refresh()
        elif index == 2:
            self.ini_page.refresh()
        elif index == 3:
            self.nginx_page.refresh()
        elif index == 4:
            self.hosts_page.refresh()
        elif index == 5:
            self.log_page.rescan()

    def _sync(self) -> None:
        active = self.php_page.mgr.active() or "未选择"
        nginx = "Nginx 运行中" if self.site_page.nginx.running() else "Nginx 未运行"
        self.statusBar().showMessage(f"PHP {active}    {nginx}")


def main() -> None:
    app = QApplication(sys.argv)
    apply_appearance(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
