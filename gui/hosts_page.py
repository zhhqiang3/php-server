"""Hosts 页：系统 hosts 里本工具管理段的增删查。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.hosts_manager import HostsManager
from gui.ui import PageHeader, danger, primary


class HostsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.mgr = HostsManager()
        self.ip = QLineEdit("127.0.0.1")
        self.ip.setMaximumWidth(140)
        self.host = QLineEdit()
        self.list = QListWidget()
        self.raw = QTextEdit()
        self.raw.setReadOnly(True)
        self.raw.setFontFamily("Consolas")

        add_btn = primary("添加")
        add_btn.clicked.connect(self.add)
        del_btn = danger("删除所选")
        del_btn.clicked.connect(self.remove)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)

        form = QHBoxLayout()
        form.setSpacing(8)
        form.addWidget(QLabel("IP"))
        form.addWidget(self.ip)
        form.addWidget(QLabel("域名"))
        form.addWidget(self.host, 1)
        form.addWidget(add_btn)
        form.addWidget(del_btn)

        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.list)
        split.addWidget(self.raw)

        self.header = PageHeader("Hosts", "系统 hosts 中由本工具管理的域名记录")
        self.header.add_action(refresh_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        layout.addWidget(self.header)
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
            QMessageBox.critical(self, "写入失败", str(exc))
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
            QMessageBox.critical(self, "删除失败", str(exc))
            return
        self.refresh()
