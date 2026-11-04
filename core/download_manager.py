"""下载管理 - 进度、速度、剩余时间、已下载/总大小"""
import time
import threading
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QProgressBar, QLabel, QHBoxLayout, QWidget

from core.php_manager import PHPManager


class DownloadProgress(QThread):
    """下载进度线程"""
    progress_update = pyqtSignal(int, int, float, float)  # 已下载, 总大小, 速度 (KB/s), 剩余时间 (秒)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, url: str, dest: str):
        super().__init__()
        self.url = url
        self.dest = dest
        self._stop = False

    def run(self):
        try:
            with requests.get(self.url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length") or 0)
                if total == 0:
                    self.progress_update.emit(0, 0, 0, 0)
                    self.finished.emit("下载完成")
                    return

                done = 0
                start_time = time.time()
                last_update = 0
                chunk_size = 1024 * 64

                with open(self.dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size):
                        if self._stop:
                            break
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        elapsed = time.time() - start_time
                        if elapsed > 1:  # 每秒更新一次
                            speed = done / elapsed / 1024 if elapsed > 0 else 0  # KB/s
                            remaining = (total - done) / speed / 1024 if speed > 0 else 0  # 秒
                            self.progress_update.emit(done, total, speed, remaining)
                            last_update = elapsed
                if not self._stop:
                    self.finished.emit("下载完成")
        except Exception as e:
            self.failed.emit(str(e))

    def stop(self):
        self._stop = True
