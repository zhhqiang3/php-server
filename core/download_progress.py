"""PHP 下载管理 - 进度显示"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QProgressBar, QLabel, QHBoxLayout, QWidget, QVBoxLayout, QFrame
)

from core.php_manager import PHPManager
from core.download_manager import DownloadProgress


class DownloadProgressBar(QFrame):
    """下载进度条 + 信息"""
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setMinimumHeight(80)

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p% (%v/%m MB)")

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666;")

        self.speed_label = QLabel("速度: -- MB/s")
        self.time_label = QLabel("剩余: --")

        layout = QVBoxLayout(self)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.time_label)

        self.progress.hide()
        self.speed_label.hide()
        self.time_label.hide()

    def show_progress(self, show: bool):
        self.progress.setVisible(show)
        self.speed_label.setVisible(show)
        self.time_label.setVisible(show)

    def update_progress(self, downloaded: int, total: int, speed: float, remaining: float):
        if total > 0:
            percent = int(downloaded / total * 100)
            self.progress.setValue(percent)
            self.progress.setFormat(f"%p% ({downloaded/1024/1024:.1f}MB / {total/1024/1024:.1f}MB)")
            self.speed_label.setText(f"速度: {speed:.1f} MB/s")
            self.time_label.setText(f"剩余: {remaining:.0f}秒")
        else:
            self.progress.setValue(0)
            self.progress.setFormat("0% (0MB / 0MB)")

    def reset(self):
        self.progress.setValue(0)
        self.progress.setFormat("0% (0MB / 0MB)")
        self.status_label.setText("就绪")
        self.speed_label.setText("速度: -- MB/s")
        self.time_label.setText("剩余: --")
