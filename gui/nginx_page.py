"""Nginx 页：安装一个 Nginx（从官网下载），启动/停止/重载。"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.nginx_manager import NginxManager
from gui.widgets import DownloadBar, DownloadTask


class NginxPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.mgr = NginxManager()

        self.state = QLabel()
        self.state.setStyleSheet("font-weight: bold;")
        self.path_label = QLabel(str(self.mgr.prefix))
        self.path_label.setStyleSheet("color: #888;")

        self.version_box = QComboBox()
        self.version_box.setMinimumWidth(160)
        refresh_btn = QPushButton("刷新版本列表")
        refresh_btn.clicked.connect(self.load_versions)
        install_btn = QPushButton("下载并安装")
        install_btn.clicked.connect(self.install)

        form = QFormLayout()
        form.addRow("安装位置", self.path_label)
        version_row = QHBoxLayout()
        version_row.addWidget(self.version_box, 1)
        version_row.addWidget(refresh_btn)
        version_row.addWidget(install_btn)
        form.addRow("官网版本", version_row)

        start_btn = QPushButton("启动")
        start_btn.clicked.connect(self.start)
        stop_btn = QPushButton("停止")
        stop_btn.clicked.connect(self.stop)
        reload_btn = QPushButton("重载配置")
        reload_btn.clicked.connect(self.reload)
        test_btn = QPushButton("测试配置")
        test_btn.clicked.connect(self.test_config)

        controls = QHBoxLayout()
        for b in (start_btn, stop_btn, reload_btn, test_btn):
            controls.addWidget(b)
        controls.addStretch(1)

        self.download = DownloadBar()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFontFamily("Consolas")
        self.log.setPlaceholderText("nginx -v / -t、启动错误等输出会显示在这里")

        layout = QVBoxLayout(self)
        layout.addWidget(self.state)
        layout.addLayout(form)
        layout.addWidget(self.download)
        layout.addLayout(controls)
        layout.addWidget(self.log, 1)

        self.refresh()

    def refresh(self) -> None:
        if self.mgr.installed():
            version = self.mgr.version() or "未知版本"
            state = "运行中" if self.mgr.running() else "未运行"
            self.state.setText(f"已安装 Nginx {version}    {state}")
        else:
            self.state.setText("未安装 Nginx —— 选择版本后点「下载并安装」")

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

    # ---------- 进程 ----------

    def start(self) -> None:
        try:
            self.mgr.start()
        except Exception as exc:  # noqa: BLE001
            self._append(str(exc))
            _err(self, "启动失败", exc)
        self.refresh()

    def stop(self) -> None:
        try:
            self.mgr.stop()
        except Exception as exc:  # noqa: BLE001
            _err(self, "停止失败", exc)
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
