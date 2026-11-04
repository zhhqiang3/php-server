"""php-cgi 进程：每个站点一个 fastcgi 后端。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from core.php_manager import PHPManager
from core.site_manager import SiteManager, cgi_port_for

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class CgiManager:
    """按站点启动/停止 php-cgi，按 (PHP 版本, 端口) 复用进程。"""

    def __init__(self) -> None:
        self.php = PHPManager()
        self.sites = SiteManager()
        self._procs: dict[tuple[str, int], subprocess.Popen] = {}

    def alive(self, version: str, port: int) -> bool:
        proc = self._procs.get((version, port))
        return proc is not None and proc.poll() is None

    def start_site(self, site: dict) -> tuple[str, int]:
        version = site.get("php") or self.php.active()
        if not version:
            raise RuntimeError(f"站点 {site['name']} 没有指定 PHP 版本")
        cgi = self.php.cgi_exe(version)
        if cgi is None:
            raise FileNotFoundError(f"未找到 PHP {version} 的 php-cgi.exe")
        port = cgi_port_for(site)
        return cgi.parent.name, self.start(cgi.parent.name, port, cgi)

    def start(self, version: str, port: int, exe: Path | None = None) -> int:
        if self.alive(version, port):
            return port
        exe = exe or self.php.cgi_exe(version)
        if exe is None:
            raise FileNotFoundError(f"未找到 PHP {version} 的 php-cgi.exe")
        proc = subprocess.Popen(
            [str(exe), "-b", f"127.0.0.1:{port}"],
            cwd=str(exe.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        self._procs[(version, port)] = proc
        return port

    def stop(self, version: str, port: int) -> None:
        proc = self._procs.pop((version, port), None)
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    def stop_all(self) -> None:
        for key in list(self._procs):
            self.stop(*key)

    def running_ports(self) -> list[tuple[str, int]]:
        return [k for k, p in self._procs.items() if p.poll() is None]
