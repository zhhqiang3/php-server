"""日志页：查看 Nginx 与 PHP 日志，自动刷新，可清空/打开所在目录。"""

from __future__ import annotations

import subprocess

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.log_manager import LogFile, nginx_logs, php_log_hint, php_logs
from core.php_manager import PHPManager
from gui.ui import PageHeader, danger


class LogPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.php = PHPManager()
        self._logs: list[LogFile] = []

        self.source = QComboBox()
        self.source.setMinimumWidth(260)
        self.source.currentIndexChanged.connect(lambda _i: self.load())
        reload_btn = QPushButton("重新扫描")
        reload_btn.clicked.connect(self.rescan)

        self.follow = QCheckBox("自动刷新")
        self.follow.setChecked(True)
        self.interval = QSpinBox()
        self.interval.setRange(1, 60)
        self.interval.setValue(2)
        self.interval.setSuffix(" 秒")
        self.interval.valueChanged.connect(self._restart_timer)
        self.follow.toggled.connect(self._restart_timer)

        open_btn = QPushButton("打开所在目录")
        open_btn.clicked.connect(self.open_dir)
        clear_btn = danger("清空此日志", "清空后不可恢复")
        clear_btn.clicked.connect(self.clear_log)
        copy_btn = QPushButton("复制全部")
        copy_btn.clicked.connect(self.copy_all)

        self.hint = QLabel("")
        self.hint.setStyleSheet("color: #b58900;")
        self.hint.setWordWrap(True)
        self.hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFontFamily("Consolas")
        self.text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(self.source, 1)
        top.addWidget(reload_btn)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(self.follow)
        controls.addWidget(QLabel("间隔"))
        controls.addWidget(self.interval)
        controls.addStretch(1)
        for b in (open_btn, clear_btn, copy_btn):
            controls.addWidget(b)

        self.header = PageHeader("日志", "Nginx 与 PHP 的运行日志")
        self.header.add_action(reload_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        layout.addWidget(self.header)
        layout.addLayout(top)
        layout.addLayout(controls)
        layout.addWidget(self.hint)
        layout.addWidget(self.text, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load)
        self._restart_timer()
        self.rescan()

    # ---------- 扫描 ----------

    def rescan(self) -> None:
        self.source.blockSignals(True)
        self.source.clear()
        self._logs = nginx_logs()
        for log in self._logs:
            self.source.addItem(f"[Nginx] {log.label}", log.path)
        active = self.php.active()
        if active:
            for log in php_logs(active):
                self._logs.append(log)
                self.source.addItem(f"[PHP {active}] {log.label}", log.path)
        self.source.blockSignals(False)
        if not self._logs:
            self.text.setPlainText("没有找到任何日志文件。\nNginx 的日志会在启动后出现在 data/nginx/logs/。")
            return
        # 保持当前选择
        current = self.source.currentData()
        idx = 0
        for log in self._logs:
            if log.path == current:
                idx = self._logs.index(log)
                break
        self.source.setCurrentIndex(idx)
        self.load()

    def _current(self) -> LogFile | None:
        idx = self.source.currentIndex()
        return self._logs[idx] if 0 <= idx < len(self._logs) else None

    # ---------- 显示 ----------

    def load(self) -> None:
        log = self._current()
        if log is None:
            return
        self.text.setPlainText(log.read())
        # 跟随滚动到底部（仅当用户本来就在底部附近）
        sb = self.text.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum() - 40
        if at_bottom:
            sb.setValue(sb.maximum())
        hint = php_log_hint(self.php.active()) if log.label.startswith("PHP") else ""
        self.hint.setText(hint or "")

    def _restart_timer(self) -> None:
        if self.follow.isChecked():
            self.timer.start(self.interval.value() * 1000)
        else:
            self.timer.stop()

    def showEvent(self, event) -> None:  # noqa: N802 — Qt 命名
        super().showEvent(event)
        if self.follow.isChecked():
            self.timer.start(self.interval.value() * 1000)

    def hideEvent(self, event) -> None:  # noqa: N802 — Qt 命名
        super().hideEvent(event)
        self.timer.stop()

    # ---------- 操作 ----------

    def open_dir(self) -> None:
        log = self._current()
        if log is None:
            return
        log.path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", "/select,", str(log.path)])

    def clear_log(self) -> None:
        log = self._current()
        if log is None:
            return
        if not log.exists():
            return
        if (
            QMessageBox.question(self, "清空", f"清空 {log.path.name}？此操作不可恢复。")
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            with log.path.open("wb"):
                pass
        except OSError as exc:
            QMessageBox.critical(self, "清空失败", str(exc))
            return
        self.load()

    def copy_all(self) -> None:
        log = self._current()
        if log is None:
            return
        text = log.read()
        QApplication.clipboard().setText(text)
        self.hint.setText(f"已复制 {len(text)} 个字符到剪贴板")
