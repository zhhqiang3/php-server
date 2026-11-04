"""站点页：站点列表（弹窗增改）、单独编辑站点配置，启动 Nginx 与 php-cgi。"""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.cgi_manager import CgiManager
from core.nginx_manager import NginxManager
from core.php_manager import PHPManager
from core.site_manager import SiteManager, cgi_port_for
from gui.site_dialog import SiteDialog


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
        self.table.itemSelectionChanged.connect(self._load_selected)
        self.table.doubleClicked.connect(self.edit)

        add_btn = QPushButton("新增站点…")
        add_btn.clicked.connect(self.add)
        edit_btn = QPushButton("编辑…")
        edit_btn.clicked.connect(self.edit)
        del_btn = QPushButton("删除所选")
        del_btn.clicked.connect(self.remove)

        buttons = QHBoxLayout()
        for b in (add_btn, edit_btn, del_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)

        # --- 站点配置编辑 ---
        self.conf_title = QLabel("站点配置：选择站点后编辑 data/sites/<名>/site.conf")
        self.conf_title.setStyleSheet("font-weight: bold;")
        self.conf = QTextEdit()
        self.conf.setFontFamily("Consolas")
        self.conf.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        save_conf_btn = QPushButton("保存配置")
        save_conf_btn.clicked.connect(self.save_conf)
        reload_conf_btn = QPushButton("重新读取")
        reload_conf_btn.clicked.connect(self._load_selected)
        regen_btn = QPushButton("按站点信息重新生成")
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
        self.cgi_check = QCheckBox("启动时同时拉起 php-cgi")
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
        left_layout.addLayout(buttons)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(left)
        split.addWidget(conf_box)
        split.setSizes([520, 460])

        layout = QVBoxLayout(self)
        layout.addWidget(split, 1)
        layout.addLayout(controls)
        layout.addLayout(self._cgi_buttons())
        self.refresh()

    # ---------- 列表 ----------

    def refresh(self) -> None:
        selected = self._selected_name()
        rows = self.sites.list_sites()
        self.table.setRowCount(len(rows))
        for i, site in enumerate(rows):
            values = [
                site.get("name", ""),
                site.get("host", ""),
                str(site.get("port", "")),
                site.get("php", ""),
                f"127.0.0.1:{cgi_port_for(site, self.php)}",
            ]
            for col, value in enumerate(values):
                self.table.setItem(i, col, QTableWidgetItem(value))

        names = [s["name"] for s in rows]
        if selected in names:
            self.table.selectRow(names.index(selected))
        elif rows:
            self.table.selectRow(0)
        else:
            self._load_selected()
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

    def _load_selected(self) -> None:
        site = self._site()
        if site is None:
            self.conf.clear()
            self.conf.setEnabled(False)
            self.conf_title.setText("站点配置：选择站点后编辑 data/sites/<名>/site.conf")
            return
        self.conf.setEnabled(True)
        self.conf_title.setText(f"站点配置：{site['name']}  data/sites/{site['name']}/site.conf")
        self.conf.setPlainText(self.sites.read_conf(site["name"]))

    # ---------- 增删改（弹窗） ----------

    def add(self) -> None:
        dlg = SiteDialog(self, self.sites, self.php)
        if dlg.exec() != SiteDialog.DialogCode.Accepted or not dlg.result_site:
            return
        self.refresh()
        site = dlg.result_site
        names = [s["name"] for s in self.sites.list_sites()]
        if site["name"] in names:
            self.table.selectRow(names.index(site["name"]))
        self.window().statusBar().showMessage(f"站点 {site['name']} 已添加，记得重载 Nginx", 5000)

    def edit(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "提示", "请先在列表中选择要编辑的站点")
            return
        old = self.sites.get(name) or {}
        dlg = SiteDialog(self, self.sites, self.php, edit_name=name)
        if dlg.exec() != SiteDialog.DialogCode.Accepted or not dlg.result_site:
            return
        site = dlg.result_site
        # 端口/域名/PHP 版本变了时，同步片段里的对应字段（保留其它手写内容）
        if (
            int(old.get("port", 0)) != int(site.get("port", 0))
            or old.get("host") != site.get("host")
            or old.get("php") != site.get("php")
        ):
            self._sync_conf_fields(name)
        self.refresh()
        self.window().statusBar().showMessage("站点信息已更新，记得重载 Nginx", 5000)

    def _sync_conf_fields(self, name: str) -> None:
        site = self.sites.get(name)
        text = self.sites.read_conf(name)
        if site is None or not text:
            return
        text = re.sub(r"(\blisten\s+)\d+", rf"\g<1>{site['port']}", text, count=1)
        text = re.sub(r"(\bserver_name\s+)\S+", rf"\g<1>{site['host']}", text, count=1)
        # PHP 版本变了，fastcgi 端口也跟着变
        cgi_port = cgi_port_for(site, self.php)
        text = re.sub(
            r"(\bfastcgi_pass\s+127\.0\.0\.1:)\d+", rf"\g<1>{cgi_port}", text, count=1
        )
        text = re.sub(r"(#\s*php version:\s*)\S+", rf"\g<1>{site.get('php', '')}", text, count=1)
        self.sites.write_conf(name, text)

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
            QMessageBox.question(self, "重新生成", "将覆盖该站点手写的配置片段，继续？")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.sites.write_conf(name, self.sites.server_block(site))
        self._load_selected()

    # ---------- Nginx / php-cgi ----------

    def start(self) -> None:
        try:
            if self.cgi_check.isChecked():
                # 上次会话遗留的 php-cgi 会占着端口，先清掉
                self.cgi.cleanup_stale()
                self.cgi.sync_all()
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
                # 配置可能变了，php-cgi 也要跟着对齐（换版本时旧进程要停）
                self.cgi.sync_all()
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
            text = "php-cgi：" + "，".join(f"{v} :{p}" for v, p in sorted(ports))
        else:
            text = "php-cgi：未运行"
        state = "运行中" if self.nginx.running() else "未运行"
        self.cgi_info.setText(f"{text}    Nginx：{state}")

    # ---------- php-cgi 单独控制 ----------

    def restart_cgi(self) -> None:
        """重启 php-cgi：按当前站点的 PHP 版本重新拉起各端口。"""
        try:
            started = self.cgi.restart_all()
        except Exception as exc:  # noqa: BLE001
            _err(self, "重启 php-cgi 失败", exc)
            self._update_cgi_info()
            return
        self._update_cgi_info()
        detail = "，".join(f"{v} :{p}" for v, p in started) if started else "无站点"
        self.window().statusBar().showMessage(f"php-cgi 已重启（{detail}）", 5000)

    def start_cgi(self) -> None:
        try:
            self.cgi.cleanup_stale()
            started = self.cgi.sync_all()
        except Exception as exc:  # noqa: BLE001
            _err(self, "启动 php-cgi 失败", exc)
            self._update_cgi_info()
            return
        self._update_cgi_info()
        detail = "，".join(f"{v} :{p}" for v, p in started) if started else "无站点"
        self.window().statusBar().showMessage(f"php-cgi 已启动（{detail}）", 5000)

    def stop_cgi(self) -> None:
        try:
            self.cgi.stop_all()
        except Exception as exc:  # noqa: BLE001
            _err(self, "停止 php-cgi 失败", exc)
        self._update_cgi_info()
        self.window().statusBar().showMessage("php-cgi 已停止", 5000)

    def _cgi_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        for label, slot in (
            ("启动 php-cgi", self.start_cgi),
            ("重启 php-cgi", self.restart_cgi),
            ("停止 php-cgi", self.stop_cgi),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        row.addStretch(1)
        return row


def _err(parent, title: str, exc: Exception) -> None:
    QMessageBox.critical(parent, title, str(exc))
