"""Nginx 页：未安装时只给安装交互，已安装后管理运行与卸载。"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.nginx_manager import NginxManager
from gui.ui import PageHeader, danger, primary
from gui.widgets import DownloadBar, DownloadTask


class NginxPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.mgr = NginxManager()

        # --- 安装区（未安装时显示） ---
        self.install_widget = QWidget()
        self.version_box = QComboBox()
        self.version_box.setMinimumWidth(160)
        self.load_versions_btn = QPushButton("刷新版本列表")
        self.load_versions_btn.clicked.connect(self.load_versions)
        install_btn = primary("下载并安装")
        install_btn.clicked.connect(self.install)

        install_form = QHBoxLayout(self.install_widget)
        install_form.setContentsMargins(0, 0, 0, 0)
        install_form.setSpacing(8)
        install_form.addWidget(QLabel("官网版本"))
        install_form.addWidget(self.version_box, 1)
        install_form.addWidget(self.load_versions_btn)
        install_form.addWidget(install_btn)

        # --- 管理区（已安装时显示） ---
        self.manage_widget = QWidget()
        self.state = QLabel()
        self.state.setStyleSheet("font-weight: bold;")
        self.path_label = QLabel(str(self.mgr.prefix))
        self.path_label.setStyleSheet("color: #888;")

        self.toggle_btn = primary("启动")
        self.toggle_btn.clicked.connect(self.toggle_run)
        reload_btn = QPushButton("重载配置")
        reload_btn.clicked.connect(self.reload)
        test_btn = QPushButton("测试配置")
        test_btn.clicked.connect(self.test_config)
        self.uninstall_btn = danger("卸载", "删除 data/nginx 整个目录")
        self.uninstall_btn.clicked.connect(self.uninstall)

        manage_row = QHBoxLayout()
        manage_row.setContentsMargins(0, 0, 0, 0)
        manage_row.setSpacing(8)
        manage_row.addWidget(self.toggle_btn)
        manage_row.addWidget(reload_btn)
        manage_row.addWidget(test_btn)
        manage_row.addStretch(1)
        manage_row.addWidget(self.uninstall_btn)

        manage_layout = QVBoxLayout(self.manage_widget)
        manage_layout.setContentsMargins(0, 0, 0, 0)
        manage_layout.setSpacing(10)
        manage_layout.addWidget(self.state)
        manage_layout.addWidget(self.path_label)
        manage_layout.addLayout(manage_row)

        self.download = DownloadBar()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFontFamily("Consolas")
        self.log.setPlaceholderText("nginx -v / -t、启动错误等输出会显示在这里")

        self.header = PageHeader("Nginx", "从官网下载一个 Windows 版并管理它的运行")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        layout.addWidget(self.header)
        layout.addWidget(self.install_widget)
        layout.addWidget(self.manage_widget)
        layout.addWidget(self.download)
        layout.addWidget(self.log, 1)

        self.refresh()

    # ---------- 刷新 ----------

    def refresh(self) -> None:
        installed = self.mgr.installed()
        self.install_widget.setVisible(not installed)
        self.manage_widget.setVisible(installed)
        if not installed:
            self.header.set_subtitle("尚未安装 —— 选择官网版本后点「下载并安装」")
            return
        version = self.mgr.version() or "未知版本"
        running = self.mgr.running()
        state = "运行中" if running else "未运行"
        self.state.setText(f"已安装 Nginx {version}    {state}")
        self._update_toggle_btn(running)
        self.header.set_subtitle(f"Nginx {version} · {state}")

    def _update_toggle_btn(self, running: bool) -> None:
        """启动/停止共用一个按钮，按状态切换文案与样式。"""
        self.toggle_btn.setText("停止" if running else "启动")
        role = "danger" if running else "primary"
        self.toggle_btn.setProperty("role", role)
        from gui.ui import restyle

        restyle(self.toggle_btn)

    # ---------- 安装 ----------

    def load_versions(self) -> None:
        try:
            versions = self.mgr.available()
        except Exception as exc:  # noqa: BLE001
            _err(self, "获取版本失败", exc)
            return
        if not versions:
            QMessageBox.warning(self, "提示", "nginx.org 上没有解析到 Windows 版本")
            return
        self.version_box.clear()
        for version, _url in versions:
            self.version_box.addItem(version)
        self._append(f"官网可下载版本：{', '.join(v for v, _ in versions[:10])} …")

    def install(self) -> None:
        if not self.version_box.count():
            self.load_versions()
            if not self.version_box.count():
                return
        version = self.version_box.currentText()
        url = None
        try:
            for v, u in self.mgr.available(refresh=False):
                if v == version:
                    url = u
                    break
        except Exception:  # noqa: BLE001 — 取缓存失败时用默认地址
            url = None
        task = DownloadTask(lambda progress, cancel: self.mgr.install(version, url, progress, cancel))
        task.done.connect(lambda v: self._installed(v))
        task.failed.connect(lambda msg: self._failed(msg))
        self.download.start(task)

    def _installed(self, version: str) -> None:
        self.refresh()
        self._append(f"已安装 Nginx {version} 到 {self.mgr.prefix}")
        QMessageBox.information(self, "安装完成", f"Nginx {version} 已安装")

    def _failed(self, msg: str) -> None:
        self.download.reset("失败")
        self._append(f"失败：{msg}")
        _err(self, "安装失败", Exception(msg))

    # ---------- 卸载 ----------

    def uninstall(self) -> None:
        version = self.mgr.version() or ""
        answer = QMessageBox.question(
            self,
            "卸载 Nginx",
            f"卸载 Nginx {version}？\n\n"
            "· 程序目录 data/nginx 会被整个删除\n"
            "· 运行中会先自动停止\n"
            "· 各站点的配置片段保留，重装后自动恢复\n",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.mgr.uninstall()
        except Exception as exc:  # noqa: BLE001
            _err(self, "卸载失败", exc)
            return
        self._append(f"已卸载 Nginx {version}")
        self.refresh()

    # ---------- 进程 ----------

    def toggle_run(self) -> None:
        """按当前状态启动或停止。"""
        if self.mgr.running():
            try:
                self.mgr.stop()
            except Exception as exc:  # noqa: BLE001
                _err(self, "停止失败", exc)
        else:
            try:
                self.mgr.start()
            except Exception as exc:  # noqa: BLE001
                self._append(str(exc))
                _err(self, "启动失败", exc)
        self.refresh()

    def reload(self) -> None:
        try:
            self.mgr.reload()
        except Exception as exc:  # noqa: BLE001
            self._append(str(exc))
            _err(self, "重载失败", exc)
        self.refresh()

    def test_config(self) -> None:
        try:
            output = self.mgr.test_config()
        except Exception as exc:  # noqa: BLE001
            self._append(str(exc))
            _err(self, "配置有误", exc)
            return
        self._append(output or "nginx -t 通过")
        QMessageBox.information(self, "配置正常", output or "nginx -t 通过")

    def _append(self, text: str) -> None:
        self.log.append(text)


def _err(parent, title: str, exc: Exception) -> None:
    QMessageBox.critical(parent, title, str(exc))
