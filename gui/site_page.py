"""站点页：新增/编辑站点，单独编辑站点配置，启动 Nginx 与 php-cgi。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.cgi_manager import CgiManager
from core.nginx_manager import NginxManager
from core.paths import ROOT
from core.php_manager import PHPManager
from core.site_manager import SiteManager, cgi_port_for


class SitePage(QWidget):
    def __init__(self, php: PHPManager) -> None:
        super().__init__()
        self.php = php
        self.sites = SiteManager()
        self.nginx = NginxManager()
        self.cgi = CgiManager()

        # --- 站点列表 ---
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["名称", "域名", "端口", "PHP", "fastcgi"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.currentCellChanged.connect(self._load_site)

        # --- 表单 ---
        self.name = QLineEdit()
        self.host = QLineEdit("127.0.0.1")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(self.sites.next_port())
        self.root = QLineEdit(str((ROOT / "data" / "www").resolve()))
        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(30)
        browse_btn.clicked.connect(self._browse_root)
        self.php_box = QComboBox()

        root_row = QHBoxLayout()
        root_row.setContentsMargins(0, 0, 0, 0)
        root_row.addWidget(self.root, 1)
        root_row.addWidget(browse_btn)

        form = QFormLayout()
        form.addRow("名称", self.name)
        form.addRow("域名", self.host)
        form.addRow("端口", self.port)
        form.addRow("网站目录", root_row)
        form.addRow("PHP", self.php_box)

        add_btn = QPushButton("新增站点")
        add_btn.clicked.connect(self.add)
        save_btn = QPushButton("保存修改")
        save_btn.clicked.connect(self.save)
        del_btn = QPushButton("删除所选")
        del_btn.clicked.connect(self.remove)
        new_btn = QPushButton("清空表单")
        new_btn.clicked.connect(self._clear_form)

        buttons = QHBoxLayout()
        for b in (add_btn, save_btn, del_btn, new_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)

        # --- 站点配置编辑 ---
        self.conf_title = QLabel("站点配置：选择左侧站点后编辑 data/sites/<名>/site.conf")
        self.conf_title.setStyleSheet("font-weight: bold;")
        self.conf = QTextEdit()
        self.conf.setFontFamily("Consolas")
        self.conf.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        save_conf_btn = QPushButton("保存配置")
        save_conf_btn.clicked.connect(self.save_conf)
        reload_conf_btn = QPushButton("重新读取")
        reload_conf_btn.clicked.connect(lambda: self._load_site(self.table.currentRow()))
        regen_btn = QPushButton("按表单重新生成")
        regen_btn.clicked.connect(self.regenerate_conf)
        test_btn = QPushButton("测试 Nginx 配置")
        test_btn.clicked.connect(self.test_config)

        conf_buttons = QHBoxLayout()
        for b in (save_conf_btn, reload_conf_btn, regen_btn, test_btn):
            conf_buttons.addWidget(b)
        conf_buttons.addStretch(1)

        conf_box = QWidget()
        conf_layout = QVBoxLayout(conf_box)
        conf_layout.setContentsMargins(0, 0, 0, 0)
        conf_layout.addWidget(self.conf_title)
        conf_layout.addWidget(self.conf, 1)
        conf_layout.addLayout(conf_buttons)

        # --- Nginx / php-cgi 控制 ---
        start_btn = QPushButton("启动 Nginx")
        start_btn.clicked.connect(self.start)
        stop_btn = QPushButton("停止 Nginx")
        stop_btn.clicked.connect(self.stop)
        reload_btn = QPushButton("重载配置")
        reload_btn.clicked.connect(self.reload)
        self.cgi_check = QCheckBox("启动站点时同时拉起 php-cgi")
        self.cgi_check.setChecked(True)
        self.cgi_info = QLabel("php-cgi：未运行")
        self.cgi_info.setStyleSheet("color: #888;")

        controls = QHBoxLayout()
        for b in (start_btn, stop_btn, reload_btn):
            controls.addWidget(b)
        controls.addWidget(self.cgi_check)
        controls.addStretch(1)
        controls.addWidget(self.cgi_info)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.table, 1)
        left_layout.addLayout(form)
        left_layout.addLayout(buttons)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(left)
        split.addWidget(conf_box)
        split.setSizes([520, 460])

        layout = QVBoxLayout(self)
        layout.addWidget(split, 1)
        layout.addLayout(controls)
        self.refresh()

    # ---------- 列表 ----------

    def refresh(self) -> None:
        selected = self._selected_name()
        rows = self.sites.list_sites()
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        for i, site in enumerate(rows):
            values = [
                site.get("name", ""),
                site.get("host", ""),
                str(site.get("port", "")),
                site.get("php", ""),
                f"127.0.0.1:{cgi_port_for(site)}",
            ]
            for col, value in enumerate(values):
                self.table.setItem(i, col, QTableWidgetItem(value))
        self.table.blockSignals(False)

        installed = self.php.installed()
        current = self.php_box.currentText()
        self.php_box.blockSignals(True)
        self.php_box.clear()
        self.php_box.addItems(installed)
        active = self.php.active()
        target = current if current in installed else active
        if target in installed:
            self.php_box.setCurrentIndex(installed.index(target))
        self.php_box.blockSignals(False)
        self.php_box.setEnabled(bool(installed))

        names = [s["name"] for s in rows]
        if selected in names:
            self.table.selectRow(names.index(selected))
        elif rows:
            self.table.selectRow(0)
        else:
            self._load_site(-1)
        self._update_cgi_info()

    def _selected_name(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.text() if item else None

    def _site(self) -> dict | None:
        name = self._selected_name()
        return self.sites.get(name) if name else None

    def _load_site(self, row: int) -> None:
        site = self._site()
        if site is None:
            self.conf.clear()
            self.conf.setEnabled(False)
            self.conf_title.setText("站点配置：选择左侧站点后编辑 data/sites/<名>/site.conf")
            return
        self.conf.setEnabled(True)
        self.conf_title.setText(f"站点配置：{site['name']}  data/sites/{site['name']}/site.conf")
        self.conf.setPlainText(self.sites.read_conf(site["name"]))
        # 表单跟随选中站点
        self.name.setText(site.get("name", ""))
        self.host.setText(site.get("host", ""))
        self.port.setValue(int(site.get("port", 8080)))
        self.root.setText(site.get("root", ""))
        idx = self.php_box.findText(site.get("php", ""))
        if idx >= 0:
            self.php_box.setCurrentIndex(idx)

    def _clear_form(self) -> None:
        self.table.clearSelection()
        self.table.setCurrentCell(-1, -1)
        self.name.clear()
        self.host.setText("127.0.0.1")
        self.root.setText(str((ROOT / "data" / "www").resolve()))
        self.port.setValue(self.sites.next_port())
        self.conf.clear()
        self.conf_title.setText("新建站点：填写左侧表单后点「新增站点」")

    def _browse_root(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择网站目录", self.root.text())
        if path:
            self.root.setText(path)

    # ---------- 增删改 ----------

    def add(self) -> None:
        try:
            site = self.sites.add(
                self.name.text(),
                self.host.text(),
                self.port.value(),
                self.root.text(),
                self.php_box.currentText(),
            )
        except Exception as exc:  # noqa: BLE001
            _err(self, "添加失败", exc)
            return
        self.refresh()
        names = [s["name"] for s in self.sites.list_sites()]
        if site["name"] in names:
            self.table.selectRow(names.index(site["name"]))
        self.port.setValue(self.sites.next_port())
        self.name.clear()

    def save(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "提示", "请先在列表中选择要修改的站点")
            return
        current = self.sites.get(name) or {}
        changed_port = int(current.get("port", 0)) != self.port.value()
        try:
            self.sites.update(
                name,
                host=self.host.text(),
                port=self.port.value(),
                root=self.root.text(),
                php_version=self.php_box.currentText(),
                # 端口/域名变了但用户没改过片段时，同步到片段里
                regenerate=False,
            )
            if changed_port or current.get("host") != self.host.text():
                self._sync_conf_fields(name)
        except Exception as exc:  # noqa: BLE001
            _err(self, "保存失败", exc)
            return
        self.refresh()
        self.window().statusBar().showMessage("站点信息已更新，记得重载 Nginx", 5000)

    def _sync_conf_fields(self, name: str) -> None:
        """只替换片段里的 listen / server_name，保留其它手写内容。"""
        import re

        site = self.sites.get(name)
        text = self.sites.read_conf(name)
        if site is None or not text:
            return
        text = re.sub(r"(\blisten\s+)\d+", rf"\g<1>{site['port']}", text, count=1)
        text = re.sub(r"(\bserver_name\s+)\S+", rf"\g<1>{site['host']}", text, count=1)
        self.sites.write_conf(name, text)
        self.conf.setPlainText(text)

    def remove(self) -> None:
        name = self._selected_name()
        if not name:
            return
        if (
            QMessageBox.question(self, "删除", f"删除站点 {name}？网站目录不会被删除。")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.sites.remove(name)
        self.refresh()
        self._clear_form()

    def save_conf(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "提示", "请先选择站点")
            return
        self.sites.write_conf(name, self.conf.toPlainText())
        self.sites.write_nginx_conf()
        self.window().statusBar().showMessage("站点配置已保存，重载 Nginx 后生效", 5000)

    def regenerate_conf(self) -> None:
        name = self._selected_name()
        site = self.sites.get(name) if name else None
        if site is None:
            return
        if (
            QMessageBox.question(self, "重新生成", "将用手写内容覆盖该站点的配置片段，继续？")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.sites.write_conf(name, self.sites.server_block(site))
        self.conf.setPlainText(self.sites.read_conf(name))

    # ---------- Nginx / php-cgi ----------

    def start(self) -> None:
        try:
            if self.cgi_check.isChecked():
                for site in self.sites.list_sites():
                    self.cgi.start_site(site)
            self.nginx.start()
        except Exception as exc:  # noqa: BLE001
            _err(self, "启动失败", exc)
            self._update_cgi_info()
            return
        self._update_cgi_info()
        self.window().statusBar().showMessage("Nginx 已启动", 5000)

    def stop(self) -> None:
        try:
            self.nginx.stop()
            self.cgi.stop_all()
        except Exception as exc:  # noqa: BLE001
            _err(self, "停止失败", exc)
        self._update_cgi_info()

    def reload(self) -> None:
        try:
            self.nginx.reload()
            if self.cgi_check.isChecked():
                for site in self.sites.list_sites():
                    self.cgi.start_site(site)
        except Exception as exc:  # noqa: BLE001
            _err(self, "重载失败", exc)
            return
        self._update_cgi_info()
        self.window().statusBar().showMessage("配置已重载", 5000)

    def test_config(self) -> None:
        try:
            output = self.nginx.test_config()
        except Exception as exc:  # noqa: BLE001
            _err(self, "配置有误", exc)
            return
        QMessageBox.information(self, "配置正常", output or "nginx -t 通过")

    def _update_cgi_info(self) -> None:
        ports = self.cgi.running_ports()
        if ports:
            text = "php-cgi：" + "，".join(f"{v} :{p}" for v, p in ports)
        else:
            text = "php-cgi：未运行"
        state = "运行中" if self.nginx.running() else "未运行"
        self.cgi_info.setText(f"{text}    Nginx：{state}")


def _err(parent, title: str, exc: Exception) -> None:
    QMessageBox.critical(parent, title, str(exc))
