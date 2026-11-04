"""PHP / Nginx 管理器主窗口。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtGui import QAction, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStatusBar,
    QTabWidget,
)

from core.php_manager import PHPManager
from gui.hosts_page import HostsPage
from gui.ini_page import IniPage
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

        tabs = QTabWidget()
        tabs.addTab(self.php_page, "PHP")
        tabs.addTab(self.site_page, "站点")
        tabs.addTab(self.ini_page, "php.ini")
        tabs.addTab(self.nginx_page, "Nginx")
        tabs.addTab(self.hosts_page, "Hosts")
        tabs.currentChanged.connect(self._on_tab)
        self.setCentralWidget(tabs)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close)
        menu = self.menuBar().addMenu("文件")
        menu.addAction(quit_action)

        self.setStatusBar(QStatusBar())
        self.php_page.changed.connect(self._sync)
        self._sync()

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

    def _sync(self) -> None:
        active = self.php_page.mgr.active() or "未选择"
        nginx = "Nginx 运行中" if self.site_page.nginx.running() else "Nginx 未运行"
        self.statusBar().showMessage(f"PHP {active}    {nginx}")


def apply_dark(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(32, 32, 32))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Base, QColor(24, 24, 24))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 40))
    palette.setColor(QPalette.ColorRole.Text, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Button, QColor(48, 48, 48))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(45, 110, 180))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)


def main() -> None:
    app = QApplication(sys.argv)
    apply_dark(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
