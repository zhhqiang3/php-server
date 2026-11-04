"""站点弹窗：新增 / 编辑站点信息。"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.hosts_manager import HostsManager, is_ip, is_local_domain
from core.paths import ROOT
from core.php_manager import PHPManager
from core.site_manager import SiteManager


class SiteDialog(QDialog):
    """新增或编辑一个站点。edit_name=None 表示新增。

    新增时域名默认 `<站点名>.local`、端口默认 80；用 .local 域名且 hosts 里
    没有时，保存时自动写入 hosts。
    """

    def __init__(
        self,
        parent,
        sites: SiteManager,
        php: PHPManager,
        edit_name: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.sites = sites
        self.php = php
        self.hosts = HostsManager()
        self.edit_name = edit_name
        self.result_site: dict | None = None
        self.hosts_added = False  # 本次保存是否往 hosts 写了记录

        current = sites.get(edit_name) if edit_name else None

        self.name = QLineEdit()
        self.host = QLineEdit(current.get("host", "") if current else "")
        self.use_ip = QCheckBox("用 IP（127.0.0.1）代替域名")
        self.use_ip.setChecked(bool(current) and is_ip(current.get("host", "")))
        self.host.setEnabled(not self.use_ip.isChecked())
        self.use_ip.toggled.connect(self._toggle_ip)
        self.host.textChanged.connect(self._update_hint)

        host_row = QHBoxLayout()
        host_row.setContentsMargins(0, 0, 0, 0)
        host_row.addWidget(self.host, 1)
        host_row.addWidget(self.use_ip)

        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self._port_touched = False
        self._setting_port = False
        # 新增默认 80；同域名已占用 80 时才往后找
        self.port.setValue(
            int(current.get("port", 0))
            if current
            else sites.next_free_port(80, self._default_host())
        )
        self.port.valueChanged.connect(self._mark_port_touched)
        self.root = QLineEdit(
            current.get("root", "") if current else str((ROOT / "data" / "www").resolve())
        )
        browse_btn = QPushButton("浏览…")
        browse_btn.clicked.connect(self._browse)
        root_row = QHBoxLayout()
        root_row.setContentsMargins(0, 0, 0, 0)
        root_row.addWidget(self.root, 1)
        root_row.addWidget(browse_btn)

        self.php_box = QComboBox()
        installed = php.installed()
        self.php_box.addItems(installed)
        if installed:
            target = (current.get("php") if current else None) or php.active()
            idx = self.php_box.findText(target)
            if idx >= 0:
                self.php_box.setCurrentIndex(idx)

        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: #888;")

        form = QFormLayout()
        form.addRow("名称", self.name)
        form.addRow("域名", host_row)
        form.addRow("端口", self.port)
        form.addRow("网站目录", root_row)
        form.addRow("PHP", self.php_box)
        form.addRow("", self.hint)

        if current:
            self.setWindowTitle(f"编辑站点：{edit_name}")
            self.name.setText(edit_name)
            self.name.setEnabled(False)  # 站点名是目录名，不允许改
        else:
            self.setWindowTitle("新增站点")
            # 域名跟着站点名走：<名>.local
            self.name.textChanged.connect(self._sync_default_host)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.resize(500, self.sizeHint().height())

        if current:
            self._update_hint()
        else:
            self._sync_default_host(self.name.text())

    # ---------- 域名 ----------

    def _default_host(self) -> str:
        """新增时的默认域名：<站点名>.local。"""
        if self.edit_name:
            return ""
        name = self.name.text().strip()
        return f"{name}.local" if name else ""

    def _mark_port_touched(self) -> None:
        """用户手动改过端口后，不再自动调整。"""
        if not self._setting_port:
            self._port_touched = True

    def _toggle_ip(self, checked: bool) -> None:
        self.host.setEnabled(not checked)
        if checked:
            self.host.setText("127.0.0.1")
        else:
            self._sync_default_host(self.name.text(), force=True)
        self._update_hint()

    def _sync_default_host(self, name: str, force: bool = False) -> None:
        """新增时域名默认 <站点名>.local；已手动改过域名就不覆盖。"""
        if self.edit_name or self.use_ip.isChecked():
            self._update_hint()
            return
        if force or not self.host.text().strip() or self.host.text().endswith(".local"):
            self.host.setText(f"{name.strip()}.local" if name.strip() else "")
        self._sync_port()
        self._update_hint()

    def _sync_port(self) -> None:
        """域名变了就重算建议端口：同域名已占用才往后找，不同域名可以共用端口。"""
        if self.edit_name or self._port_touched:
            return
        host = self.host.text().strip()
        self._setting_port = True
        try:
            self.port.setValue(self.sites.next_free_port(80, host))
        finally:
            self._setting_port = False

    def _update_hint(self) -> None:
        host = self.host.text().strip()
        if self.use_ip.isChecked() or is_ip(host):
            self.hint.setText("使用 IP 访问，不需要改 hosts。")
            return
        if not host:
            self.hint.setText("")
            return
        if is_local_domain(host):
            try:
                exists = self.hosts.contains(host)
            except OSError as exc:
                self.hint.setText(f"检查 hosts 失败：{exc}")
                return
            self.hint.setText(
                f"hosts 里已有 {host}，无需修改。"
                if exists
                else f"{host} 是本地域名，保存时会自动写入 hosts。"
            )
        else:
            self.hint.setText("公网域名，不会修改 hosts。")

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择网站目录", self.root.text())
        if path:
            self.root.setText(path)

    # ---------- 保存 ----------

    def _save(self) -> None:
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "站点名不能为空")
            return
        host = self.host.text().strip() or "127.0.0.1"
        try:
            if self.edit_name:
                self.result_site = self.sites.update(
                    self.edit_name,
                    host=host,
                    port=self.port.value(),
                    root=self.root.text(),
                    php_version=self.php_box.currentText(),
                )
            else:
                self.result_site = self.sites.add(
                    name,
                    host,
                    self.port.value(),
                    self.root.text(),
                    self.php_box.currentText(),
                )
        except Exception as exc:  # noqa: BLE001 — 表单校验错误直接显示在弹窗里
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        if not self._ensure_hosts(host):
            return
        self.accept()

    def _ensure_hosts(self, host: str) -> bool:
        """本地域名不在 hosts 里就写一条；写失败提示但不撤销站点。"""
        if not is_local_domain(host):
            return True
        try:
            if self.hosts.ensure("127.0.0.1", host):
                self.hosts_added = True
        except Exception as exc:  # noqa: BLE001 — hosts 写不了（多半是缺管理员权限）
            QMessageBox.warning(
                self,
                "hosts 未写入",
                f"站点已创建，但没能把 {host} 写进 hosts：\n{exc}\n\n"
                "请以管理员身份运行本工具，或手动在 hosts 里加一行：\n"
                f"127.0.0.1\t{host}",
            )
        return True
