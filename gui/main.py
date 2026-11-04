"""PHP / Nginx 管理器主窗口。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.hosts_manager import HostsManager
from core.ini_editor import IniEditor
from core.nginx_manager import NginxManager
from core.php_manager import PHPManager
from core.site_manager import SiteManager


def _err(parent, title: str, exc: Exception) -> None:
    QMessageBox.critical(parent, title, str(exc))


class InstallThread(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, major: str) -> None:
        super().__init__()
        self.major = major

    def run(self) -> None:
        try:
            version = PHPManager().install_latest(
                self.major, progress=lambda d, t: self.progress.emit(d, t)
            )
            self.done.emit(version)
        except Exception as exc:  # noqa: BLE001 — 界面要显示任何下载/解压错误
            self.failed.emit(str(exc))


class PhpPage(QWidget):
    changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.mgr = PHPManager()
        self.major = QComboBox()
        self.major.addItems(self.mgr.majors)
        self.list = QListWidget()
        self.active = QLabel("当前版本：未选择")

        install_btn = QPushButton("安装该主版本最新版")
        install_btn.clicked.connect(self.install)
        use_btn = QPushButton("设为当前版本")
        use_btn.clicked.connect(self.use)
        remove_btn = QPushButton("删除所选版本")
        remove_btn.clicked.connect(self.remove)

        row = QHBoxLayout()
        row.addWidget(QLabel("主版本"))
        row.addWidget(self.major, 1)
        row.addWidget(install_btn)

        actions = QHBoxLayout()
        actions.addWidget(use_btn)
        actions.addWidget(remove_btn)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.active)
        layout.addLayout(row)
        layout.addWidget(self.list, 1)
        layout.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for name in self.mgr.installed():
            self.list.addItem(name)
        active = self.mgr.active() or "未选择"
        self.active.setText(f"当前版本：{active}")

    def install(self) -> None:
        major = self.major.currentText()
        self.active.setText(f"正在下载 PHP {major} …")
        self.thread = InstallThread(major)
        self.thread.done.connect(self._installed)
        self.thread.failed.connect(lambda msg: _err(self, "安装失败", Exception(msg)))
        self.thread.failed.connect(lambda _m: self.refresh())
        self.thread.start()

    def _installed(self, version: str) -> None:
        self.mgr.use(version)
        self.refresh()
        self.changed.emit()
        QMessageBox.information(self, "安装完成", f"已安装并切换到 PHP {version}")

    def _selected(self) -> str | None:
        item = self.list.currentItem()
        return item.text() if item else None

    def use(self) -> None:
        version = self._selected()
        if not version:
            return
        try:
            self.mgr.use(version)
        except Exception as exc:  # noqa: BLE001
            _err(self, "切换失败", exc)
            return
        self.refresh()
        self.changed.emit()

    def remove(self) -> None:
        version = self._selected()
        if not version:
            return
        if QMessageBox.question(self, "删除", f"删除 PHP {version}？") != QMessageBox.StandardButton.Yes:
            return
        self.mgr.remove(version)
        self.refresh()
        self.changed.emit()


class SitePage(QWidget):
    def __init__(self, php: PHPManager) -> None:
        super().__init__()
        self.php = php
        self.sites = SiteManager()
        self.nginx = NginxManager()

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["名称", "域名", "端口", "PHP"])
        self.table.horizontalHeader().setStretchLastSection(True)

        self.name = QLineEdit()
        self.host = QLineEdit("127.0.0.1")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(self.sites.next_port())
        self.root = QLineEdit(str((ROOT / "data" / "www").resolve()))
        self.php_box = QComboBox()

        form = QFormLayout()
        form.addRow("名称", self.name)
        form.addRow("域名", self.host)
        form.addRow("端口", self.port)
        form.addRow("网站目录", self.root)
        form.addRow("PHP", self.php_box)

        add_btn = QPushButton("添加站点")
        add_btn.clicked.connect(self.add)
        del_btn = QPushButton("删除所选")
        del_btn.clicked.connect(self.remove)
        start_btn = QPushButton("启动 Nginx")
        start_btn.clicked.connect(self.start)
        stop_btn = QPushButton("停止 Nginx")
        stop_btn.clicked.connect(self.stop)
        reload_btn = QPushButton("重载配置")
        reload_btn.clicked.connect(self.reload)

        buttons = QHBoxLayout()
        for b in (add_btn, del_btn, start_btn, stop_btn, reload_btn):
            buttons.addWidget(b)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table, 1)
        layout.addLayout(form)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        self.php_box.clear()
        installed = self.php.installed()
        self.php_box.addItems(installed or ["（尚未安装 PHP）"])
        active = self.php.active()
        if active:
            idx = self.php_box.findText(active)
            if idx >= 0:
                self.php_box.setCurrentIndex(idx)
        rows = self.sites.list_sites()
        self.table.setRowCount(len(rows))
        for i, site in enumerate(rows):
            for col, key in enumerate(("name", "host", "port", "php")):
                self.table.setItem(i, col, QTableWidgetItem(str(site.get(key, ""))))
        self.port.setValue(self.sites.next_port())

    def add(self) -> None:
        try:
            self.sites.add(
                self.name.text(),
                self.host.text(),
                self.port.value(),
                self.root.text(),
                self.php_box.currentText(),
            )
        except Exception as exc:  # noqa: BLE001
            _err(self, "添加失败", exc)
            return
        self.name.clear()
        self.refresh()

    def remove(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        self.sites.remove(item.text())
        self.refresh()

    def start(self) -> None:
        try:
            self.nginx.start()
        except Exception as exc:  # noqa: BLE001
            _err(self, "启动失败", exc)

    def stop(self) -> None:
        try:
            self.nginx.stop()
        except Exception as exc:  # noqa: BLE001
            _err(self, "停止失败", exc)

    def reload(self) -> None:
        try:
            self.nginx.reload()
        except Exception as exc:  # noqa: BLE001
            _err(self, "重载失败", exc)


class IniPage(QWidget):
    def __init__(self, php: PHPManager) -> None:
        super().__init__()
        self.php = php
        self.editor = IniEditor()
        self.version = QComboBox()
        self.version.currentTextChanged.connect(self.load)
        self.text = QTextEdit()
        self.text.setFontFamily("Consolas")
        save_btn = QPushButton("保存（自动备份）")
        save_btn.clicked.connect(self.save)
        reload_btn = QPushButton("重新读取")
        reload_btn.clicked.connect(self.load)

        top = QHBoxLayout()
        top.addWidget(QLabel("版本"))
        top.addWidget(self.version, 1)
        top.addWidget(reload_btn)
        top.addWidget(save_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.text, 1)

    def refresh(self) -> None:
        current = self.version.currentText()
        self.version.blockSignals(True)
        self.version.clear()
        self.version.addItems(self.php.installed())
        idx = self.version.findText(current)
        if idx >= 0:
            self.version.setCurrentIndex(idx)
        self.version.blockSignals(False)
        self.load()

    def load(self) -> None:
        version = self.version.currentText()
        if not version:
            self.text.clear()
            return
        try:
            self.text.setPlainText(self.editor.read(version))
        except Exception as exc:  # noqa: BLE001
            self.text.setPlainText(f"无法读取：{exc}")

    def save(self) -> None:
        version = self.version.currentText()
        if not version:
            return
        try:
            backup = self.editor.save(version, self.text.toPlainText())
        except Exception as exc:  # noqa: BLE001
            _err(self, "保存失败", exc)
            return
        QMessageBox.information(self, "已保存", f"备份：{backup.name}")


class HostsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.mgr = HostsManager()
        self.ip = QLineEdit("127.0.0.1")
        self.host = QLineEdit()
        self.list = QListWidget()
        self.raw = QTextEdit()
        self.raw.setReadOnly(True)
        self.raw.setFontFamily("Consolas")

        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add)
        del_btn = QPushButton("删除所选")
        del_btn.clicked.connect(self.remove)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)

        form = QHBoxLayout()
        form.addWidget(QLabel("IP"))
        form.addWidget(self.ip)
        form.addWidget(QLabel("域名"))
        form.addWidget(self.host, 1)
        form.addWidget(add_btn)
        form.addWidget(del_btn)
        form.addWidget(refresh_btn)

        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.list)
        split.addWidget(self.raw)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(split, 1)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        try:
            for ip, host in self.mgr.entries():
                self.list.addItem(f"{ip}  {host}")
            self.raw.setPlainText(self.mgr.read())
        except Exception as exc:  # noqa: BLE001
            self.raw.setPlainText(f"读取 hosts 失败：{exc}")

    def add(self) -> None:
        try:
            self.mgr.add(self.ip.text(), self.host.text())
        except Exception as exc:  # noqa: BLE001
            _err(self, "写入失败", exc)
            return
        self.host.clear()
        self.refresh()

    def remove(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        host = item.text().split()[-1]
        try:
            self.mgr.remove(host)
        except Exception as exc:  # noqa: BLE001
            _err(self, "删除失败", exc)
            return
        self.refresh()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PHP / Nginx 管理器")
        self.resize(980, 680)

        self.php_page = PhpPage()
        self.site_page = SitePage(self.php_page.mgr)
        self.ini_page = IniPage(self.php_page.mgr)
        self.hosts_page = HostsPage()

        tabs = QTabWidget()
        tabs.addTab(self.php_page, "PHP")
        tabs.addTab(self.site_page, "站点")
        tabs.addTab(self.ini_page, "php.ini")
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
        if index == 1:
            self.site_page.refresh()
        elif index == 2:
            self.ini_page.refresh()
        elif index == 3:
            self.hosts_page.refresh()

    def _sync(self) -> None:
        active = self.php_page.mgr.active() or "未选择"
        nginx = "运行中" if self.site_page.nginx.running() else "未运行"
        self.statusBar().showMessage(f"PHP {active}    Nginx {nginx}")


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
