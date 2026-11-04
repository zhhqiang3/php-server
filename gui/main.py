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
)

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
        self.tabs = tabs
        tabs.addTab(self.site_page, "站点")
        tabs.addTab(self.php_page, "PHP")
        tabs.addTab(self.ini_page, "php.ini")
        tabs.addTab(self.nginx_page, "Nginx")
        tabs.addTab(self.hosts_page, "Hosts")
        tabs.addTab(self.log_page, "日志")
        # php.ini 页不直接显示，从 PHP 列表点「查看配置」进入
        tabs.setTabVisible(self._index_of(tabs, self.ini_page), False)
        tabs.currentChanged.connect(self._on_tab)
        self.setCentralWidget(tabs)

        self._build_menus()

        self.setStatusBar(QStatusBar())
        self.php_page.changed.connect(self._sync)
        # PHP 列表点「查看配置」-> 切到 php.ini 页
        self.php_page.view_ini_requested.connect(self.show_ini)
        # php.ini 页点「返回」-> 回到 PHP 列表
        self.ini_page.closed.connect(self.show_php)
        self._sync()

    @staticmethod
    def _index_of(tabs: QTabWidget, widget) -> int:
        for i in range(tabs.count()):
            if tabs.widget(i) is widget:
                return i
        return -1

    def show_ini(self, version: str) -> None:
        """打开 php.ini 配置页并定位到指定版本。"""
        idx = self._index_of(self.tabs, self.ini_page)
        if idx < 0:
            return
        self.tabs.setCurrentIndex(idx)
        self.ini_page.show_version(version)

    def show_php(self) -> None:
        """回到 PHP 列表页。"""
        idx = self._index_of(self.tabs, self.php_page)
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)

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
        widget = self.tabs.widget(index)
        if widget is self.php_page:
            self.php_page.refresh()
        elif widget is self.site_page:
            self.site_page.refresh()
        elif widget is self.ini_page:
            self.ini_page.refresh()
        elif widget is self.nginx_page:
            self.nginx_page.refresh()
        elif widget is self.hosts_page:
            self.hosts_page.refresh()
        elif widget is self.log_page:
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
