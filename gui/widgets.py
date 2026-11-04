"""下载任务线程与进度条控件。"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QProgressBar, QPushButton, QWidget


class DownloadTask(QThread):
    """在后台执行一个返回 str 的任务，并把进度转成信号。"""

    progress = pyqtSignal(int, int, float, float)  # 已下载, 总大小, 速度 B/s, 剩余秒
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, fn: Callable[..., str], parent=None) -> None:
        super().__init__(parent)
        self.fn = fn
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        try:
            result = self.fn(progress=self._emit_progress, cancel=self.is_cancelled)
            self.done.emit(str(result))
        except InterruptedError as exc:
            self.failed.emit(str(exc) or "已取消")
        except Exception as exc:  # noqa: BLE001 — 界面要显示任何下载/解压错误
            self.failed.emit(str(exc))

    def _emit_progress(self, downloaded: int, total: int, speed: float, eta: float) -> None:
        self.progress.emit(downloaded, total, speed, eta)


class DownloadBar(QWidget):
    """下载进度条：百分比、大小、速度、剩余时间、取消按钮。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(True)
        self.bar.setFormat("就绪")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setVisible(False)
        self.task: DownloadTask | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.bar, 1)
        layout.addWidget(self.cancel_btn)

    def start(self, task: DownloadTask) -> None:
        self.task = task
        self.bar.setValue(0)
        self.bar.setFormat("准备下载…")
        self.cancel_btn.setVisible(True)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.clicked.connect(task.cancel)
        task.progress.connect(self.on_progress)
        task.finished.connect(self.on_finished)
        task.start()

    def on_progress(self, done: int, total: int, speed: float, eta: float) -> None:
        if total > 0:
            self.bar.setValue(int(done * 1000 / total))
            self.bar.setFormat(
                f"{done * 100 / total:.1f}%  "
                f"{_mb(done)}/{_mb(total)}  "
                f"{speed / 1024 / 1024:.2f} MB/s  剩余 {_duration(eta)}"
            )
        else:
            self.bar.setRange(0, 0)
            self.bar.setFormat(f"{_mb(done)}  {speed / 1024 / 1024:.2f} MB/s")

    def on_finished(self) -> None:
        self.cancel_btn.setVisible(False)
        if self.bar.maximum() == 0:
            self.bar.setRange(0, 1000)
        self.bar.setValue(1000)
        self.bar.setFormat("完成")

    def reset(self, text: str = "就绪") -> None:
        self.task = None
        self.cancel_btn.setVisible(False)
        if self.bar.maximum() == 0:
            self.bar.setRange(0, 1000)
        self.bar.setValue(0)
        self.bar.setFormat(text)


def _mb(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB"


def _duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds <= 0:
        return "--"
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m{seconds % 60:02d}s"
