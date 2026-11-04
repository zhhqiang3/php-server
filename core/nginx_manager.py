"""Nginx 进程：查找 nginx.exe、启动、停止、重载。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from core.paths import resolve
from core.site_manager import SiteManager


class NginxManager:
    def __init__(self) -> None:
        self.sites = SiteManager()
        self.prefix = self.sites.nginx_dir

    def exe(self) -> Path | None:
        local = self.prefix / "nginx.exe"
        if local.exists():
            return local
        found = shutil.which("nginx")
        return Path(found) if found else None

    def running(self) -> bool:
        pid = self.prefix / "logs" / "nginx.pid"
        if not pid.exists():
            return False
        try:
            n = int(pid.read_text(encoding="utf-8").strip())
        except ValueError:
            return False
        # tasklist 过滤，避免依赖 psutil
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {n}", "/NH"],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return str(n) in (out.stdout or "")

    def start(self) -> None:
        exe = self.exe()
        if exe is None:
            raise FileNotFoundError(
                "未找到 nginx.exe。请把 nginx 解压到 data/nginx，或加入 PATH。"
            )
        self.sites.write_nginx_conf()
        self._run([str(exe), "-p", str(self.prefix), "-c", "conf/nginx.conf"])

    def stop(self) -> None:
        exe = self.exe()
        if exe is None:
            return
        self._run([str(exe), "-p", str(self.prefix), "-s", "stop"], check=False)

    def reload(self) -> None:
        exe = self.exe()
        if exe is None:
            raise FileNotFoundError("未找到 nginx.exe")
        self.sites.write_nginx_conf()
        if self.running():
            self._run([str(exe), "-p", str(self.prefix), "-s", "reload"])
        else:
            self.start()

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=str(self.prefix),
            capture_output=True,
            text=True,
            check=check,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


def nginx_dir() -> Path:
    return resolve("data/nginx")
