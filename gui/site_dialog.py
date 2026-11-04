"""站点弹窗：新增 / 编辑站点信息。"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.paths import ROOT
from core.php_manager import PHPManager
from core.site_manager import SiteManager


class SiteDialog(QDialog):
    """新增或编辑一个站点。edit_name=None 表示新增。"""

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
        self.edit_name = edit_name
        self.result_site: dict | None = None

        current = sites.get(edit_name) if edit_name else None

        self.name = QLineEdit()
        self.host = QLineEdit(current.get("host", "127.0.0.1") if current else "127.0.0.1")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(int(current.get("port", 0)) if current else sites.next_port())
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

        form = QFormLayout()
        form.addRow("名称", self.name)
        form.addRow("域名", self.host)
        form.addRow("端口", self.port)
        form.addRow("网站目录", root_row)
        form.addRow("PHP", self.php_box)

        if current:
            self.setWindowTitle(f"编辑站点：{edit_name}")
            self.name.setText(edit_name)
            self.name.setEnabled(False)  # 站点名是目录名，不允许改
        else:
            self.setWindowTitle("新增站点")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.resize(460, self.sizeHint().height())

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择网站目录", self.root.text())
        if path:
            self.root.setText(path)

    def _save(self) -> None:
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "站点名不能为空")
            return
        try:
            if self.edit_name:
                self.result_site = self.sites.update(
                    self.edit_name,
                    host=self.host.text(),
                    port=self.port.value(),
                    root=self.root.text(),
                    php_version=self.php_box.currentText(),
                )
            else:
                self.result_site = self.sites.add(
                    name,
                    self.host.text(),
                    self.port.value(),
                    self.root.text(),
                    self.php_box.currentText(),
                )
        except Exception as exc:  # noqa: BLE001 — 表单校验错误直接显示在弹窗里
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self.accept()
