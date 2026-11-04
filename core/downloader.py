"""通用下载：流式写入、进度回调、取消。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

import requests

ProgressFn = Callable[[int, int, float, float], None]  # 已下载, 总大小, 速度 B/s, 剩余秒


def download(
    url: str,
    dest: Path,
    progress: Optional[ProgressFn] = None,
    cancel: Optional[Callable[[], bool]] = None,
    chunk_size: int = 64 * 1024,
) -> Path:
    """把 url 下载到 dest。progress 每秒回调一次。取消时删除半成品并抛 InterruptedError。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    with requests.get(url, stream=True, timeout=(15, 60)) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        done = 0
        start = time.monotonic()
        last = start
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size):
                if cancel and cancel():
                    raise InterruptedError("下载已取消")
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                now = time.monotonic()
                if progress and now - last >= 0.3:
                    last = now
                    speed = done / max(now - start, 1e-6)
                    eta = (total - done) / speed if speed > 0 and total > done else 0.0
                    progress(done, total, speed, eta)
        if cancel and cancel():
            raise InterruptedError("下载已取消")
        tmp.replace(dest)
        if progress:
            elapsed = max(time.monotonic() - start, 1e-6)
            progress(done, total or done, done / elapsed, 0.0)
    return dest
